# คู่มือทำ Tutorial 6 แบบ step by step

งานเดี่ยว ส่งเป็น **URL ของ fork ตัวเอง** ใน MyCourseVille (กำหนดส่งดูจากประกาศของวิชา)

ทำตามลำดับในคู่มือนี้ และรันทุกคำสั่งใน **terminal ของ WSL** ไม่ใช่ PowerShell ของ Windows

## ภาพรวมสถานะ

- [x] เตรียม environment (`.venv` และ packages)
- [x] เขียนโค้ด Task 1–3 (`tests/` ผ่าน 12/12 แต่ยังไม่ได้ commit)
- [ ] ขั้นที่ 1: เปิด terminal 2 หน้าต่าง
- [ ] ขั้นที่ 2: วัด Task 0 และ `t1-before` บนโค้ดเดิม
- [ ] ขั้นที่ 3: เอาโค้ด fallback กลับมา แล้ววัด `t1-after`
- [ ] ขั้นที่ 4: วัด Task 2
- [ ] ขั้นที่ 5: วัด Task 3
- [ ] ขั้นที่ 6: กรอก `worksheet/task1-3.md`
- [ ] ขั้นที่ 7: ทำ `worksheet/task4.md`
- [ ] ขั้นที่ 8: ตรวจรายการส่ง แล้ว commit, push และส่ง URL

## ข้อควรจำ

- **Restart `run_all.py` ทุกครั้งที่โค้ดเปลี่ยน** (Ctrl+C แล้วรันใหม่) ไม่อย่างนั้น load test จะวัดโค้ดเก่า
- **จด run time เอง:** บรรทัด `finished in ... s` แสดงใน terminal เท่านั้น ไม่ถูกบันทึกลง `results/runs.csv` ต้องจดของ `t1-before` และ `t1-after` ไว้ทันที
- **ทุกครั้งที่รัน load test จะต่อแถวใหม่ใน `results/runs.csv`** ถ้ารันซ้ำชื่อเดิมจะมีแถวซ้ำ ให้ใช้แถวล่าสุด
- **Run ที่เกี่ยวกับ cascade ต้องใช้โค้ด Task 2** และ `t3-cache` ต้องใช้โค้ด Task 3 ซึ่งมีอยู่แล้วใน `inference_service/patterns.py`

## ขั้นที่ 1: เปิด terminal 2 หน้าต่าง

ทำเหมือนกันทั้งสองหน้าต่าง:

```bash
cd ~/master-degree/software-architecture-2026/swarch-arch4AI
source .venv/bin/activate
```

- **Terminal 1:** ใช้รัน `python run_all.py`
- **Terminal 2:** ใช้รัน load test และ `pytest`

## ขั้นที่ 2: วัด Task 0 และ `t1-before` บนโค้ดเดิม

`t1-before` ต้องวัดตอน**ยังไม่มี** fallback แต่ตอนนี้ใส่ fallback ไปแล้ว จึงต้องเอาไฟล์เดิมกลับมาชั่วคราว

**Terminal 2:** เก็บโค้ด fallback ไว้ชั่วคราว

```bash
git stash push review_service/fallback.py
```

**Terminal 1:** เปิด services แล้วรอจนเห็น "All services are up"

```bash
python run_all.py
```

**Terminal 2:** รันทีละคำสั่ง

```bash
python tools/loadtest.py --name t0-large
python tools/loadtest.py --name t0-small --strategy small
python tools/loadtest.py --name t1-before --hang-rate 0.1
```

จด `finished in ... s` ของ `t1-before` ไว้

## ขั้นที่ 3: เอาโค้ด fallback กลับมา แล้ววัด `t1-after`

**Terminal 1:** กด Ctrl+C เพื่อหยุด services

**Terminal 2:**

```bash
git stash pop
python -m pytest tests/
```

ต้องผ่าน 12/12 ถ้าไม่ผ่าน แปลว่าโค้ด fallback อาจยังไม่กลับมา ให้เช็กด้วย `git status` และ `git stash list`

**Terminal 1:** เปิด services ใหม่

```bash
python run_all.py
```

**Terminal 2:**

```bash
python tools/loadtest.py --name t1-after --hang-rate 0.1
```

จด `finished in ... s` ของ `t1-after` ไว้

## ขั้นที่ 4: วัด Task 2

**Terminal 2:** (services จากขั้นที่ 3 ใช้ต่อได้เลย)

```bash
python tools/loadtest.py --name t2-0.6 --strategy cascade --threshold 0.6
python tools/loadtest.py --name t2-0.7 --strategy cascade --threshold 0.7
python tools/loadtest.py --name t2-0.8 --strategy cascade --threshold 0.8
python tools/loadtest.py --name t2-0.9 --strategy cascade --threshold 0.9
```

ดูผลเทียบกับ QR3 (accuracy อย่างน้อย 90%) และ QR4 (ใช้ large model ให้น้อยที่สุด) แล้วเลือก threshold ที่จะใช้

## ขั้นที่ 5: วัด Task 3

แทน `<threshold>` ด้วยค่าที่เลือกจากขั้นที่ 4:

```bash
python tools/loadtest.py --name t3-cache --strategy cascade --threshold <threshold> --cache on
```

จากนั้นกด Ctrl+C ที่ Terminal 1 เพื่อหยุด services ได้

**ตรวจผล:** `results/runs.csv` ต้องมีครบ 9 run: `t0-large`, `t0-small`, `t1-before`, `t1-after`, `t2-0.6`, `t2-0.7`, `t2-0.8`, `t2-0.9`, `t3-cache`

## ขั้นที่ 6: กรอก [`worksheet/task1-3.md`](../worksheet/task1-3.md)

ตอบข้อละ 1–3 ประโยค ภาษาไทยหรืออังกฤษก็ได้

- [ ] กรอกชื่อและรหัสนิสิต
- [ ] Task 0: ตาราง และ Q0
- [ ] Task 1: ตาราง (run time มาจากที่จดไว้) และ Q1.1–Q1.4
- [ ] Task 2: ตาราง และ Q2.1–Q2.3
- [ ] Task 3: ตาราง และ Q3.1–Q3.2
- [ ] Debrief: Q4

## ขั้นที่ 7: ทำ [`worksheet/task4.md`](../worksheet/task4.md)

- [ ] กรอกชื่อและรหัสนิสิต
- [ ] เลือก scenario ตามเลขตัวสุดท้ายของรหัสนิสิต: เลขคี่เลือก A หรือ B, เลขคู่เลือก B หรือ C
- [ ] ส่วนที่ 1: quality requirements 3 ข้อ พร้อมตัวเลขเมื่อทำได้
- [ ] ส่วนที่ 2: เลือก topology (T1–T4) และ pattern ที่เพิ่ม
- [ ] ส่วนที่ 2: วาด C4 container diagram ด้วย Mermaid (ดูตัวอย่าง syntax ใน `README.md`)
- [ ] ส่วนที่ 3: อ้างชื่อ run และตัวเลขจาก `results/runs.csv`
- [ ] ส่วนที่ 3: ถ้าเลือก scenario A ต้องแสดงการคำนวณจำนวน large-model calls ต่อวินาทีช่วงพีค
- [ ] ส่วนที่ 4: ADR ครบ Title, Status, Context, Decision, Consequences (Positive และ Negative) และ Alternatives อย่างน้อย 1 topology

## ขั้นที่ 8: ตรวจรายการส่ง แล้วส่งงาน

### รายการที่ต้องส่ง

| สิ่งที่ส่ง | ไฟล์ | สิ่งที่ต้องมี |
|---|---|---|
| โค้ด Task 1 | `review_service/fallback.py` | `classify()` |
| โค้ด Task 2 และ 3 | `inference_service/patterns.py` | `cascade()` และ `PredictionCache` |
| ผลการวัด | `results/runs.csv` | ครบ 9 run |
| Worksheet | `worksheet/task1-3.md` | ตารางครบ และคำถามครบ 11 ข้อ |
| Task 4 | `worksheet/task4.md` | ครบทั้ง 4 ส่วน |

### คำสั่งส่งงาน

```bash
python -m pytest tests/
git add worksheet/ results/ review_service/ inference_service/
git commit -m "Tutorial 6"
git push
```

จากนั้นเปิด fork บน GitHub เช็กว่าไฟล์ขึ้นครบ แล้วส่ง **URL ของ fork** ใน MyCourseVille

คำสั่ง `git add` นี้ไม่รวมโฟลเดอร์ `note/` คู่มือนี้จึงไม่ถูกส่งไปด้วย

## ส่วนที่ AI ช่วยได้และไม่ได้

ตาม [`AGENTS.md`](../AGENTS.md):

- **ช่วยได้:** เขียนโค้ด Task 1–3, รัน test และ load test, คัดลอกตัวเลขจาก `results/runs.csv` ลงตารางใน worksheet, อธิบายแนวคิด
- **ต้องทำเอง:** คำตอบของคำถามใน worksheet, ADR และเหตุผลการออกแบบใน `task4.md`

## แก้ปัญหาที่เจอบ่อย

| ปัญหา | วิธีแก้ |
|---|---|
| `Cannot reach the services` | เช็กว่า `python run_all.py` รันอยู่ใน Terminal 1 |
| `address already in use` | `run_all.py` รอบก่อนยังรันอยู่ ให้กด Ctrl+C หรือปิด terminal นั้น |
| แก้โค้ดแล้วไม่มีผล | restart `run_all.py` |
| `ModuleNotFoundError` | activate `.venv` และรันคำสั่งจาก root ของ repo |
| `t1-before` ได้ผลเหมือน `t1-after` | ลืม `git stash` หรือลืม restart ให้ทำขั้นที่ 2 ใหม่ แล้วใช้แถวล่าสุดใน `results/runs.csv` |
