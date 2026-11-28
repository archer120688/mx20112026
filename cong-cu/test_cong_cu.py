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
qb = nap("quang_ba", "cong-cu/quang-ba.py")
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
    KENH = {"facebook_link": "https://www.facebook.com/share/19UdefbYnF/", "youtube_link": "ĐIỀN: dán link", "facebook_nhung": "",
            "youtube_kenh_id": ""}
    BAI = [("2026-11-29", "Mời <b>bạn</b> ghé", ["Đoạn một", "Đoạn hai"], "Mời bạn ghé\n\nĐoạn một")]

    def test_loc(self):
        self.assertNotIn("0912345678", dt.loc("gọi 0912345678 hoặc a@b.com ở thay-cap/thu.csv"))

    def test_chua_co_youtube(self):
        h = dt.dung(self.KENH, self.BAI)
        self.assertIn("Mỗi ngày đều ra video mới", h)
        self.assertIn("share/19UdefbYnF", h)
        self.assertNotIn("Mở kênh YouTube", h)
        self.assertNotIn("<b>bạn</b>", h)

    def test_co_youtube_va_nhung(self):
        k = dict(self.KENH, youtube_link="https://www.youtube.com/@abc", youtube_kenh_id="UC" + "a" * 22,
                 facebook_nhung="https://www.facebook.com/tentrang")
        h = dt.dung(k, [])
        self.assertIn("https://www.youtube.com/@abc", h)
        self.assertIn("list=UU" + "a" * 22, h)
        self.assertIn("plugins/page.php", h)

    def test_link_hong(self):
        with self.assertRaises(ValueError):
            dt.dung(dict(self.KENH, facebook_link="ĐIỀN"), [])


class TestQuangBa(unittest.TestCase):
    K = {"facebook_link": "https://www.facebook.com/share/19UdefbYnF/", "youtube_link": "", "mo_ta": "", "facebook_nhung": "",
         "youtube_kenh_id": ""}
    THAN = "Bạn có từng bỏ lỡ một video hay chỉ vì quên theo dõi trang không? Mỗi ngày trang đều ra video mới, bạn ghé xem một chút nhé."

    def bai(self, than=None, tieu="Đừng lỡ video mới"):
        return "# %s\n\n%s %s\n" % (tieu, than or self.THAN, self.K["facebook_link"])

    def test_dat(self):
        self.assertEqual(qb.loi_bai(self.bai(), self.K), [])

    def test_thieu_link(self):
        self.assertTrue(any("link Facebook" in x for x in qb.loi_bai("# Tiêu đề hay\n\n" + self.THAN, self.K)))

    def test_link_la_va_cau_cam(self):
        loi = " | ".join(qb.loi_bai(self.bai(self.THAN + " Xem ngay http://x.vn, đảm bảo 100% hay"), self.K))
        self.assertIn("link lạ", loi)
        self.assertIn("câu cấm", loi)

    def test_khuon(self):
        self.assertTrue(qb.loi_bai("không có tiêu đề", self.K))
        self.assertTrue(qb.loi_bai(self.bai("Ngắn quá"), self.K))


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
