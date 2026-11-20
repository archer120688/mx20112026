import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vi

CS = {
    "han_muc_ngay": {"gemini": 100, "san-pham": 5, "video": 3, "bai-dang": 12},
    "nguong": {"tiet_kiem": 0.70, "dung": 0.90},
    "ngay_khong_thu_phai_ra_soat": 14,
}


class TestVi(unittest.TestCase):
    def setUp(self):
        self.cn = vi.ket_noi(":memory:")
        self._dung = vi.FILE_DUNG
        vi.FILE_DUNG = os.path.join(tempfile.mkdtemp(), "DUNG")

    def tearDown(self):
        vi.FILE_DUNG = self._dung

    def test_ghi_thu_va_trung(self):
        self.assertEqual(vi.ghi_thu(self.cn, 50000, "A1", "sao kê", "donate", "ngan-hang")[0], "DA_GHI")
        self.assertEqual(vi.ghi_thu(self.cn, 50000, "A1", "sao kê", "donate", "ngan-hang")[0], "TRUNG")
        self.assertEqual(vi.thong_ke(self.cn)["thu"], 50000)

    def test_ghi_thu_khong_hop_le(self):
        for args in [(0, "A", "x", "donate"), (-5, "A", "x", "donate"), (1000, "", "x", "donate"),
                     (1000, "A", "", "donate"), (1000, "A", "x", "khac"), (10.5, "A", "x", "donate")]:
            self.assertEqual(vi.ghi_thu(self.cn, *args)[0], "TU_CHOI")
        self.assertEqual(vi.ghi_thu(self.cn, 1000, "A", "x", "donate", "agent")[0], "TU_CHOI")

    def test_chuoi_bam(self):
        for i in range(3):
            vi.ghi_thu(self.cn, 1000 * (i + 1), "M%d" % i, "bc", "shopee", "shopee")
        self.assertTrue(vi.kiem_tra(self.cn)[0])
        with self.assertRaises(Exception):  # trigger chặn sửa
            self.cn.execute("UPDATE but_toan SET so_tien=999999 WHERE id=1")
        with self.assertRaises(Exception):
            self.cn.execute("DELETE FROM but_toan WHERE id=2")
        # kẻ gỡ trigger rồi sửa → chuỗi băm phải báo hỏng
        self.cn.execute("DROP TRIGGER khong_sua_but_toan")
        self.cn.execute("UPDATE but_toan SET so_tien=999999 WHERE id=2")
        ok, _, ly_do = vi.kiem_tra(self.cn)
        self.assertFalse(ok)
        self.assertIn("id=2", ly_do)

    def test_xin_quota_gioi_han(self):
        for _ in range(3):
            self.assertEqual(vi.xin_quota(self.cn, CS, "video", 1)[0], "DUYET")
        self.assertEqual(vi.xin_quota(self.cn, CS, "video", 1)[0], "TU_CHOI")
        self.assertEqual(vi.xin_quota(self.cn, CS, "khong-co", 1)[0], "TU_CHOI")
        self.assertEqual(vi.xin_quota(self.cn, CS, "gemini", 1)[0], "TU_CHOI")  # gemini do script nền ghi
        self.assertEqual(vi.xin_quota(self.cn, CS, "bai-dang", 0)[0], "TU_CHOI")

    def test_trang_thai_theo_quota(self):
        self.assertEqual(vi.trang_thai_song(self.cn, CS), "ACTIVE")
        vi.ghi_quota(self.cn, "gemini", 70)
        self.assertEqual(vi.trang_thai_song(self.cn, CS), "THRIFT_MODE")
        self.assertEqual(vi.xin_quota(self.cn, CS, "san-pham", 1)[0], "TU_CHOI")
        self.assertEqual(vi.xin_quota(self.cn, CS, "video", 1)[0], "DUYET")
        vi.ghi_quota(self.cn, "gemini", 20)
        self.assertEqual(vi.trang_thai_song(self.cn, CS), "HALTED")
        self.assertEqual(vi.xin_quota(self.cn, CS, "video", 1)[0], "TU_CHOI")

    def test_sang_ngay_moi_quota_ve_0(self):
        vi.ghi_quota(self.cn, "gemini", 95)
        self.assertEqual(vi.trang_thai_song(self.cn, CS), "HALTED")
        self.cn.execute("UPDATE quota SET ngay='2000-01-01'")
        self.assertEqual(vi.trang_thai_song(self.cn, CS), "ACTIVE")

    def test_dung_va_tam_dung(self):
        open(vi.FILE_DUNG, "w").close()
        self.assertEqual(vi.trang_thai_song(self.cn, CS), "KILL_SWITCH")
        os.remove(vi.FILE_DUNG)
        self.cn.execute("INSERT OR REPLACE INTO he_thong VALUES('tam_dung','1')")
        self.assertEqual(vi.trang_thai_song(self.cn, CS), "PAUSED_BY_OWNER")

    def test_bao_cao_va_ra_soat(self):
        self.cn.execute("UPDATE he_thong SET gia_tri='2000-01-01' WHERE khoa='ngay_bat_dau'")
        txt = vi.bao_cao(self.cn, CS)
        self.assertIn("PHẢI RÀ SOÁT", txt)
        vi.ghi_thu(self.cn, 20000, "Z", "bc", "donate", "chu")
        txt = vi.bao_cao(self.cn, CS)
        self.assertNotIn("PHẢI RÀ SOÁT", txt)
        self.assertIn("20.000đ", txt)
        self.assertIn("toàn vẹn", txt)


if __name__ == "__main__":
    unittest.main()
