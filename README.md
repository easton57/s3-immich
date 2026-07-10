# s3-immich

Upload files from a local directory to an S3 bucket. Originally written to back up an Immich instance, but it works for any set of files -- just point UPLOAD_DIR at whatever you want to sync.

## Setup

Copy env.example to .env and fill in the values:

```
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=
S3_BUCKET=
UPLOAD_DIR=
```

Install dependencies:

```
pip install -r requirements.txt
```

## Usage

```
python immich-s3-sync.py
```

Optional environment variables:

- `AWS_SESSION_TOKEN` -- for temporary credentials
- `S3_ENDPOINT_URL` -- for S3-compatible services (MinIO, Backblaze B2, DigitalOcean Spaces, etc.)
- `EXTRA_ARGS` -- JSON string of extra arguments passed to the S3 upload. For example: `{"StorageClass": "DEEP_ARCHIVE"}`
- `VERSIONING` -- set to any value to skip the duplicate check and upload everything (useful if bucket versioning is enabled)

I use it as a cron job, must be run as immich user or files won't be able to be read media.

## How it works

1. Validates that all required environment variables are set.
2. Scans UPLOAD_DIR recursively for files.
3. If VERSIONING is not set, lists existing objects in the bucket and skips files whose basename already exists.
4. Uploads all new files to S3_BUCKET with the configured storage class and extra args.
5. Reports a summary of successes and failures, and exits with code 1 if any uploads failed.

## Extra args

At minimum you should set a storage class. Options: STANDARD, STANDARD_IA, ONEZONE_IA, GLACIOR_INSTANT, GLACIER_FLEXIBLE, DEEP_ARCHIVE.

Other supported upload args are documented in the [boto3 S3 transfer docs](https://docs.aws.amazon.com/boto3/latest/reference/customizations/s3.html#boto3.s3.transfer.S3Transfer.ALLOWED_UPLOAD_ARGS).
