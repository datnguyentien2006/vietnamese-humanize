from app.services.rewriter import list_available_models

try:
    models = list_available_models()
    print("=== MODELS KHẢ DỤNG CHO KEY CỦA BẠN ===")
    for m in models:
        print(f"  {m}")
except Exception as e:
    print(f"Lỗi: {type(e).__name__}: {e}")