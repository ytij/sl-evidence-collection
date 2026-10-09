import unittest

import timestamp


class TestTimestamp(unittest.TestCase):
    def test_build_request_structure(self):
        req = timestamp.build_request(b"\x01" * 32, 12345)
        self.assertEqual(req[0], 0x30)  # SEQUENCE
        _tag, outer, _ = timestamp._tlv(req, 0)
        _tag, version, _ = timestamp._tlv(outer, 0)
        self.assertEqual(int.from_bytes(version, "big"), 1)
        _tag, imprint, _ = timestamp._tlv(outer, 3)  # after INTEGER version
        self.assertEqual(imprint[0], 0x30)  # MessageImprint SEQUENCE

    def test_parse_status(self):
        granted = timestamp._der(0x30, timestamp._der(0x30, timestamp._der_int(0)))
        self.assertEqual(timestamp.parse_status(granted), 0)
        rejected = timestamp._der(0x30, timestamp._der(0x30, timestamp._der_int(2)))
        self.assertEqual(timestamp.parse_status(rejected), 2)

    def test_der_int_sign_bit(self):
        # 0xFF must be encoded with a leading 0x00 to stay positive.
        enc = timestamp._der_int(0xFF)
        self.assertEqual(enc, bytes([0x02, 0x02, 0x00, 0xFF]))


if __name__ == "__main__":
    unittest.main()
