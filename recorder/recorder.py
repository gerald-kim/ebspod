#!/usr/bin/env python
# encoding: utf-8
"""
recorder.py

Created by Jaewoo Kim on 2008-12-11.
Copyright (c) 2008 __MyCompanyName__. All rights reserved.
"""

import sys
import os
import time
import datetime
import subprocess
import signal
import eyeD3
import urllib2
import S3
import simplejson
from sys import exit

from recorder_settings import *

def get_waittime( start ): 
    n = datetime.datetime.now()
    start_time = datetime.datetime.strptime( start, '%H:%M:%S' )
    s = n.replace( hour = start_time.hour, minute = start_time.minute, second = 0)
    diff = s-n
    if diff.seconds > 1000:
        return 0
    return diff.seconds
    
def get_duration_in_second( start, end ):
    n = datetime.datetime.now()
    start_time = datetime.datetime.strptime( start, '%H:%M:%S' )
    end_time = datetime.datetime.strptime( end, '%H:%M:%S' )
    diff = end_time - start_time
    return diff.seconds

def mark_status( p_id, status ):
    u = urllib2.urlopen( '%s/update_status/%s/?status=%s' % ( SERVER_ADDR, p_id, status ) )
    u.read()
    u.close()
    
def update_id3_tag( filename, program, title):
    tag = eyeD3.Tag()
    tag.link( filename )
    tag.header.setVersion(eyeD3.ID3_V2_4)
    tag.setTextEncoding( eyeD3.frames.UTF_8_ENCODING )
    tag.setAlbum( program )
    tag.setArtist( u"ebspod" )
    tag.setTitle( title )
    tag.update()
    
def record( filename, start, end ):
    f = open( filename, 'w+' )
    null = open( '/dev/null', 'w' )
	
    p = subprocess.Popen( ["/usr/local/bin/ebs"], stdout=f, stderr=null )
    
    time.sleep(get_duration_in_second(start,end))
    #time.sleep( 5 )
    os.kill( p.pid, signal.SIGTERM )

    f.close()

def upload_to_s3( filename ):
    conn = S3.AWSAuthConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    conn.calling_format = S3.CallingFormat.PATH

    key = os.path.basename( filename )

    f = open( filename )
    r = conn.put( BUCKET_NAME, key, S3.S3Object(f.read()), {'x-amz-acl': 'public-read', 'Content-Type': 'audio/mp3'})
    if r.http_response.status != 200:
        print "upload fail."
        exit( 1 )

    
def main():
    programjson = urllib2.urlopen( '%s/scheduled/' % ( SERVER_ADDR ) ).read()
    try:
        program = simplejson.loads( programjson )
    except ValueError:
	print 'Nothing to record'
        exit(0)
    print program
    
    title = "%s-%s" % ( program['title'].encode('utf-8'), datetime.datetime.now().strftime("%Y%m%d") )
    filename = '%s%s_%s.mp3' % ( '/tmp/', program['id'], datetime.datetime.now().strftime("%Y%m%d%H%M") )
    print filename
    
    try:
        mark_status( program['id'], 'ready' )
        print( "Waiting %d seconds to program begin." % ( get_waittime( program['start'] ) ) )
        time.sleep(get_waittime(program['start']))
        print( "Start recording %s for %d seconds " % ( title,  get_duration_in_second( program['start'], program['end'] ) ) )
    
        mark_status( program['id'], 'recording' )
        record( filename, program['start'], program['end']  )
        update_id3_tag( filename, program['title'], title )
        upload_to_s3( filename )
        urllib2.urlopen( '%s/save_episode/?program_id=%s&url=http://s3.amazonaws.com/ebspod/%s' 
            % ( SERVER_ADDR, program['id'], os.path.basename( filename ) ) ).read()
        
    finally:
        mark_status( program['id'], 'pending' )


if __name__ == '__main__':
	main()

