import React from "react";

export const Disclaimer: React.FC = () => {
  return (
    <div className="bg-sky-50/70 dark:bg-sky-950/40 border border-sky-200/80 dark:border-sky-800/60 rounded-xl p-4 shadow-card mb-6 transition-colors">
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-sky-100 dark:bg-sky-900/60 text-sky-700 dark:text-sky-300 flex items-center justify-center mt-0.5">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
          </svg>
        </div>
        <div className="flex-1 text-xs sm:text-sm">
          <h3 className="font-bold text-sky-950 dark:text-sky-200 flex items-center gap-2">
            <span>Phạm vi & mục đích công cụ</span>
            <span className="text-[10px] font-mono px-2 py-0.2 rounded-full bg-sky-100 dark:bg-sky-900/60 text-sky-800 dark:text-sky-300 font-semibold border border-sky-200 dark:border-sky-800">
              Biên tập viên
            </span>
          </h3>
          <p className="text-slate-600 dark:text-slate-300 mt-1 leading-relaxed">
            Công cụ Humanize chuyển văn bản có phong cách AI thành văn viết tự
            nhiên mà vẫn giữ nguyên sự kiện, số liệu và ý của tác giả. Mỗi kết
            quả chỉ là <strong>đề xuất</strong> để tác giả tự rà soát và quyết
            định. Công cụ <strong>không</strong> đo xác suất AI,{" "}
            <strong>không</strong> suy đoán tác giả và{" "}
            <strong>không có tính năng lách kiểm duyệt</strong>.
          </p>
        </div>
      </div>
    </div>
  );
};

