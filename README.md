IoT Honeypot Testbet

ขอบเขตตอนนี้คือมัน จำลองพฤติกรรมและสร้าง trace ในเครื่อง ครับ ยังไม่ได้เชื่อมต่อหรือส่งคำสั่งไปยัง MQTT, CoAP, ESP32 หรืออุปกรณ์จริง และยังไม่ใช่ระบบตรวจจับการโจมตีจริง ถ้าเปิดเว็บแล้วกดรัน ลำดับที่เลือกจะกลายเป็นบันทึกเหตุการณ์จำลองให้ดูใน dashboard ครับ

MVP สำหรับงานวิจัยระดับปริญญาตรีที่ทำงานภายในเครื่องเท่านั้น ใช้สำหรับสร้าง Behavioral Trace ของพฤติกรรม IoT แบบสังเคราะห์ตามลำดับเหตุการณ์ โดยแต่ละ Scenario จะเรียกใช้พฤติกรรมจำลองที่กำหนดไว้ล่วงหน้า

ระบบนี้ ไม่มีการรองรับ การเชื่อมต่อไปยังเป้าหมายภายนอก, URL ที่กำหนดเอง, คำสั่ง Shell หรือ Payload สำหรับการโจมตีจริง

สถาปัตยกรรมและการไหลของข้อมูล
Browser UI
    ↓
FastAPI Scenario Controller
    ↓
ชุดพฤติกรรมจำลองที่กำหนดไว้ล่วงหน้า
    ↓
Trace Collector / Database Layer
    ↓
SQLite
    ↓
ตาราง Trace และ Session Timeline

ไฟล์ backend/main.py ทำหน้าที่เป็น REST API และให้บริการหน้าเว็บ Frontend

ภายในระบบมี ACTIONS ซึ่งเป็นชุดพฤติกรรมที่กำหนดไว้ล่วงหน้า โดยทำหน้าที่เป็น จุดเชื่อมต่อสำหรับเปลี่ยนจาก Mock Handler ไปเป็น Adapter ของ Testbed จริงในอนาคต

เมื่อแต่ละขั้นตอนของ Scenario ได้รับการยอมรับ ระบบจะสร้าง Event ตามลำดับ โดยบันทึกข้อมูลดังนี้:

เวลา UTC
Session ID
Source ID
Service
Behavior Label
Result
ระยะเวลาระหว่าง Event

ข้อมูลจะถูกจัดเก็บใน SQLite โดยแบ่งเป็น:

Sessions
Events
Behavioral Sequences

ไฟล์ฐานข้อมูลอยู่ที่:

data/honeypot.sqlite3
การรันระบบภายในเครื่อง

ต้องใช้ Python 3.10 ขึ้นไป

เปิด PowerShell แล้วใช้คำสั่ง:

py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8000

จากนั้นเปิด:

http://127.0.0.1:8000

ระบบควรผูกกับ 127.0.0.1 เพื่อให้ทำงานเฉพาะภายในเครื่องสำหรับการพัฒนา

ฐานข้อมูลจะถูกสร้างขึ้นโดยอัตโนมัติที่:

data/honeypot.sqlite3
API

ระบบมี API หลักดังนี้:

GET  /api/status
GET  /api/scenarios
GET  /api/sessions
GET  /api/events
GET  /api/statistics

GET  /api/sessions/{session_id}

POST /api/scenarios/run

ตัวอย่างการเรียกใช้:

{
  "steps": [
    "service_discovery",
    "mqtt_connect"
  ],
  "source_id": "attacker-emulator",
  "delay_ms": 350
}

ระบบจะตรวจสอบทุก Behavior ว่าอยู่ใน ชุดพฤติกรรมที่กำหนดไว้อย่างปลอดภัย หรือไม่

ข้อกำหนดของข้อมูล:

source_id รองรับตัวอักษร ตัวเลข _ และ -
ระยะเวลาหน่วงอยู่ระหว่าง 100–5000 มิลลิวินาที
หนึ่ง Scenario มีได้สูงสุด 30 ขั้นตอน

login_attempt จะถูกแทนด้วย Event จำลองที่ถูกปฏิเสธ

ส่วน Mock Event อื่น ๆ เป็นเพียงการจำลองหรือการบันทึกเหตุการณ์ที่ไม่เป็นอันตรายภายในระบบ

ขอบเขตของ MVP

ในเวอร์ชันนี้ Mock Service จะสร้าง Trace Record ภายในโปรแกรมโดยตรง

ยังไม่มีการ:

เปิด MQTT Listener จริง
เปิด CoAP Listener จริง
ควบคุม Hardware จริง
เชื่อมต่อกับระบบภายนอก

ในอนาคตสามารถเพิ่ม Adapter สำหรับ:

Service Log จริง
ข้อมูล Metadata จาก Network Packet
Device Log
Raspberry Pi
ESP32
MQTT
CoAP

โดยนำ Adapter เหล่านี้เชื่อมต่อผ่าน ACTIONS และ Trace Collector Schema ที่มีอยู่แล้ว

การเก็บข้อมูลในอนาคตต้องจำกัดอยู่ภายใน IoT Testbed ที่ควบคุมได้ของโครงงานเท่านั้น

สรุปสั้น ๆ ของ MVP นี้
ผู้ใช้เลือก Scenario
        ↓
เลือก Behavior ตามลำดับ
        ↓
ระบบจำลองพฤติกรรม
        ↓
สร้าง Event
        ↓
Trace Collector
        ↓
SQLite
        ↓
Behavioral Trace
        ↓
แสดง Session Timeline
