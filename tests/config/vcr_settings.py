''' Settings involving the test of online functionality '''

import vcr

TAPE = vcr.VCR(
    cassette_library_dir='/tests/cassettes',
    filter_headers=['Authorization'],
    serializer='json'
)