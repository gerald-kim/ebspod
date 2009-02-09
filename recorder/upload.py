import S3
import os
from recorder_settings import *

def upload_to_s3( filename ):
    conn = S3.AWSAuthConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
#    conn.calling_format = S3.CallingFormat.PATH
    generator = S3.QueryStringAuthGenerator(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

    key = os.path.basename( filename )

    f = open( filename )
    r = conn.put( BUCKET_NAME, key, S3.S3Object(f.read()), {'x-amz-acl': 'public-read', 'Content-Type': 'audio/mp3'})
    if r.http_response.status != 200:
        print "upload fail."
        exit( 1 )
    


def main():
    upload_to_s3( 'a.mp3' )
if __name__ == '__main__':
    main()
