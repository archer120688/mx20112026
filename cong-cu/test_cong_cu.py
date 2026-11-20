import importlib.util, os, sys, tempfile, unittest, json

AQ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(AQ, "kiem-soat"))
import vi


def nap(ten, tep):
    s = importlib.util.spec_from_file_location(ten, os.path.join(AQ, tep))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


kb = nap("kiem_bai", "cong-cu/kiem-bai.py")
dt = nap("dung_trang", "cong-cu/dung-trang.py")
nt = nap("nhap_thu", "kiem-soat/nhap-thu.py")
bv = nap("bao_ve_so", "cong-cu/bao-ve-so.py")

LINK = "https://s.shopee.vn/AbC123"
BAI_TOT = "Chảo 24cm, xem giá ở link: %s\nCó link tiếp thị Shopee, mình có thể nhận hoa hồng khi bạn mua.\n" % LINK


def goi(d, bai, nguon="tự tạo bằng script lam-video"):
    os.makedirs(d, exist_ok=True)
    for ten, nd, che in (("video.mp4", b"x", "wb"), ("bai-dang.md", bai, "w"), ("nguon.txt", nguon, "w")):
        with open(os.path.join(d, ten), che, **({} if che == "wb" else {"encoding": "utf-8"})) as f:
            f.write(nd)


class TestKiemBai(unittest.TestCase):
    def test_dat(self):
        d = tempfile.mkdtemp()
        goi(d, BAI_TOT)
        self.assertEqual(kb.kiem_goi(d, {LINK}), [])

    def test_loi(self):
        d = tempfile.mkdtemp()
        goi(d, "Mình đã dùng thử, hiệu quả 100%% %s" % LINK)
        loi = " | ".join(kb.kiem_goi(d, {LINK}))
        self.assertIn("hoa hồng", loi)
        self.assertIn("câu cấm", loi)

    def test_link_la(self):
        d = tempfile.mkdtemp()
        goi(d, BAI_TOT)
        self.assertTrue(any("link-affiliate" in x for x in kb.kiem_goi(d, set())))

    def test_thieu_tep(self):
        d = tempfile.mkdtemp()
        self.assertEqual(len(kb.kiem_goi(d, set())), 3)  # thiếu đủ 3 tệp, chưa có bài để kiểm tiếp

    def test_nguon_trong(self):
        d = tempfile.mkdtemp()
        goi(d, BAI_TOT, nguon="")
        self.assertTrue(any("nguon.txt" in x for x in kb.kiem_goi(d, {LINK})))


class TestNhapThu(unittest.TestCase):
    def test_nhap(self):
        cn = vi.ket_noi(":memory:")
        tep = os.path.join(tempfile.mkdtemp(), "thu.csv")
        with open(tep, "w", encoding="utf-8") as f:
            f.write("ma_giao_dich,ngay,so_tien,loai_thu,nguon,ghi_chu\n"
                    "FT1,2026-11-20,\"50.000đ\",donate,ngan-hang,\nSP1,2026-11-21,12000,shopee,shopee,hoa hồng tuần 47\n"
                    "LOI,2026-11-21,0,donate,chu,\n")
        self.assertEqual(nt.nhap(tep, cn), (3, 2))
        self.assertEqual(nt.nhap(tep, cn), (3, 0))  # chạy lại không ghi trùng
        self.assertEqual(vi.thong_ke(cn)["thu"], 62000)


class TestTrang(unittest.TestCase):
    TK = {"ma_ngan_hang": "vcb", "so_tai_khoan": "123", "ten_chu_tai_khoan": "NGUYEN VAN A", "muc_dich": "Duy trì dự án"}

    def test_chua_dien(self):
        with self.assertRaises(ValueError):
            dt.kiem_tra_tai_khoan(dict(self.TK, muc_dich="ĐIỀN: gì đó"))
        dt.kiem_tra_tai_khoan(self.TK)

    def test_loc_va_dung(self):
        self.assertNotIn("0912345678", dt.loc("gọi 0912345678 hoặc a@b.com ở thay-cap/thu.csv"))
        so = dict(thu=62000, donate=50000, shopee=12000, ngay_chay=3, ngay_khong_thu=0)
        h = dt.dung(self.TK, so, [("2026-11-20", "Ngày <1>", ["làm <b>x</b>"])], "abc")
        self.assertIn("62.000đ", h)
        self.assertNotIn("<b>x</b>", h)
        self.assertIn("img.vietqr.io/image/vcb-123", h)
        self.assertIn("hoa hồng", h)


class TestBaoVeSo(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.db = os.path.join(self.d, "so.db")
        self.an = os.path.join(self.d, "an-toan.db")
        cn = vi.ket_noi(self.db)
        vi.ghi_thu(cn, 20000, "A1", "bc", "donate", "chu")
        vi.ghi_quota(cn, "video", 1)
        cn.close()
        bv.chup(self.db, self.an)

    def dc(self, khoa=""):
        return bv.doi_chieu(self.db, self.an, khoa)

    def test_hop_le_duoc_giu(self):
        cn = vi.ket_noi(self.db)
        vi.ghi_quota(cn, "video", 1)          # agent xin quota hợp lệ → thêm dòng
        cn.close()
        self.assertEqual(self.dc(), "OK")

    def test_sua_so_thu_bi_khoi_phuc(self):
        cn = vi.ket_noi(self.db)
        cn.execute("DROP TRIGGER khong_sua_but_toan")
        cn.execute("UPDATE but_toan SET so_tien=9999999")
        cn.close()
        self.assertIn("KHÔI PHỤC", self.dc())
        self.assertEqual(vi.thong_ke(vi.ket_noi(self.db))["thu"], 20000)

    def test_xoa_quota_bi_khoi_phuc(self):
        cn = vi.ket_noi(self.db)
        cn.execute("DELETE FROM quota")
        cn.close()
        self.assertIn("quota", self.dc())

    def test_khoa_api_lot_vao_so(self):
        cn = vi.ket_noi(self.db)
        vi.ghi_nhat_ky(cn, "agent", "x", "ok", {"k": "AIzaSyTESTKEY12345"})
        cn.close()
        self.assertEqual(self.dc(), "OK")                       # không có khoá thì không sao
        self.assertIn("khoá API", self.dc("AIzaSyTESTKEY12345"))

    def test_so_hong_hoac_mat(self):
        with open(self.db, "wb") as f:
            f.write(b"khong phai sqlite" * 100)
        self.assertIn("KHÔI PHỤC", self.dc())
        os.remove(self.db)
        self.assertIn("bị xoá", self.dc())
        self.assertTrue(vi.kiem_tra(vi.ket_noi(self.db))[0])


if __name__ == "__main__":
    unittest.main()
