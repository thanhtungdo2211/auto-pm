## Tổng quan
- Ứng dụng FastAPI đóng vai trò trung tâm, cung cấp webhook Zalo, endpoint chatbot thử nghiệm và scheduler cho các tác vụ định kỳ.
- Hệ thống tự động: nhắc nhân viên gửi báo cáo cuối ngày, lưu báo cáo vào Plane, tổng hợp báo cáo ngày trước gửi quản lý, gửi danh sách task hằng ngày.
- Tích hợp chính: Zalo OA (gửi/nhận tin), Chatbot (CHATBOT_MANAGER_URL), Plane API (lấy/sinh daily-progress), Qdrant (lưu lịch sử/embedding), Scheduler (APScheduler).

## Kiến trúc thành phần
- `app/main.py`: khởi tạo FastAPI, CORS, healthcheck, include router `webhooks`, `chatbot`, khởi động/ shutdown scheduler.
- `app/scheduler.py`: định nghĩa các job Cron:
  - `send_daily_task_notifications` (gửi danh sách task hôm nay cho từng user).
  - `send_daily_report_request` (18h, nhắc staff gửi báo cáo; gửi qua chatbot với `mode_report=True`).
  - `send_previous_day_manager_report` (08h, tổng hợp báo cáo hôm trước cho manager; gọi chatbot với `mode_report=True` rồi gửi Zalo).
  - `send_manager_summary` (08:30, dùng `manager_report_service` gửi summary hôm qua).
  - Job dùng `MANAGER_ZALO_IDS` (list Zalo ID, phân tách bằng dấu phẩy).
- Routers:
  - `app/routers/webhooks.py`: endpoint `/api/zalo/webhook`, xử lý sự kiện Zalo qua `ZaloWebhookService`; tự phát hiện báo cáo ngày, gọi `ReportHandler` để lưu daily-progress lên Plane; dùng `query_today_task` để lấy task theo user. Có endpoint phụ xem conversation, pending registrations…
  - `app/routers/chatbot.py`: endpoint thử `/api/chatbot/chat` gọi `ChatbotAgentService.get_conversation_response` (dùng `send_query` đơn giản).
- Services chính:
  - `services/zalo_service.py`: client Zalo OA (gửi message, lấy conversation, tải file…).
  - `services/zalo_webhook_service.py`: nghiệp vụ webhook, tích hợp chatbot (long-memory qua Qdrant), xử lý đăng ký, CV, báo cáo, ghi lịch sử vào Qdrant, fallback.
  - `services/chatbot_agent_service.py`: gọi chatbot qua HTTP. Hàm mới `send_chat_request(user_id, role, query, mode_report, file_content)` hỗ trợ scheduler; các hàm cũ `send_query`, `send_query_with_file`, `send_long_memory`.
  - `services/query_today_task.py`: lấy dự án/issue từ Plane, map user→tasks (lọc theo ngày), hỗ trợ save JSON kết quả.
  - `services/report_handler.py`: parse báo cáo text, tạo payload daily-progress và lưu lên Plane cho từng issue của user.
  - `services/previous_day_report_service.py`: tổng hợp daily-progress của ngày hôm trước, format message (dùng cho scheduler/manager).
  - `services/manager_report_service.py`: thu thập báo cáo hôm qua, format và gửi cho manager (cách cũ, vẫn còn).
  - Khác: `analysis_cv.py` (phân tích CV), `vector_db_client.py` (Qdrant), parser báo cáo.

## Luồng chính
1) Webhook inbound (Zalo → `/api/zalo/webhook`):
   - Xử lý idempotent qua `processed_events`.
   - Nếu là báo cáo cuối ngày: lấy tasks người dùng (`query_today_task`), parse và lưu daily-progress (`ReportHandler`), trả lời user.
   - Chat tự do: gọi chatbot (hiện dùng `send_long_memory` + Qdrant để lưu lịch sử; fallback gửi xin lỗi).
   - Các nhánh khác: đăng ký user, phê duyệt HR, xử lý file/CV.

2) Scheduler (APScheduler):
   - 08:00: `send_previous_day_manager_report` → gọi `aggregate_previous_day_reports` → format → gửi chatbot `mode_report=True` → gửi Zalo cho manager.
   - 08:30: `send_manager_summary` (luồng cũ) gửi trực tiếp qua Zalo.
   - 18:00: `send_daily_report_request` → prompt chatbot `mode_report=True` soạn lời nhắc → gửi Zalo cho từng staff.
   - (Cấu hình giờ thực tế đang đặt 10:29/10:30 trong code demo; cần chỉnh CronTrigger nếu muốn đúng 8:00/18:00.)

3) Lưu báo cáo vào Plane:
   - `ReportHandler` gọi Plane API `/daily-progress/` với payload từ `report_parser`.
   - `previous_day_report_service` và `manager_report_service` đọc daily-progress để tổng hợp.

4) Chatbot integration:
   - Endpoint chatbot hiện yêu cầu các tham số: `user_id`, `role`, `query`, `file_content`, `mode_report`.
   - Scheduler/webhook khi cần chế độ báo cáo bật `mode_report=True`; chatbot có thể trả về `mode_report` cập nhật.

## Biến môi trường chính
- `CHATBOT_MANAGER_URL`: URL API chatbot.
- `ZALO_ACCESS_TOKEN`, `ZALO_BASE_URL`: cấu hình OA.
- `PLANE_API_URL`, `PLANE_API_KEY`, `WORKSPACE_SLUG`: kết nối Plane.
- `MANAGER_ZALO_IDS`: danh sách Zalo ID quản lý (phân tách dấu phẩy).

## File/Module quan trọng
- Ứng dụng & scheduler: `app/main.py`, `app/scheduler.py`.
- Webhook & chatbot route: `app/routers/webhooks.py`, `app/routers/chatbot.py`.
- Chatbot client: `services/chatbot_agent_service.py`.
- Zalo OA: `services/zalo_service.py`, `services/zalo_webhook_service.py`.
- Báo cáo & Plane: `services/report_handler.py`, `services/query_today_task.py`, `services/previous_day_report_service.py`, `services/manager_report_service.py`.

## Ghi chú vận hành nhanh
- Chạy dev: `uvicorn app.main:app --reload --host 0.0.0.0 --port 5544` (hoặc theo README).
- Đảm bảo thiết lập biến môi trường ở trên; kiểm tra token Zalo/Plane và URL chatbot.
- Điều chỉnh giờ CronTrigger trong `app/scheduler.py` nếu cần đúng 08:00/18:00 thực tế.

