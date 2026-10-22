import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { Disclaimer } from "./Disclaimer";

test("hiển thị câu khẳng định rõ phạm vi: không đo AI, không suy đoán tác giả", () => {
  const { container } = render(<Disclaimer />);
  const text = container.textContent ?? "";

  expect(screen.getByText("Phạm vi & mục đích công cụ")).toBeInTheDocument();
  expect(text).toContain("Công cụ không đo xác suất AI");
  expect(text).toContain("không suy đoán tác giả");
  expect(text).toContain("Mỗi kết quả chỉ là đề xuất");
});

test("không chứa từ ngữ overclaim (bypass, detector, đo lường AI)", () => {
  const { container } = render(<Disclaimer />);
  const text = (container.textContent ?? "").toLowerCase();

  expect(text).not.toContain("bypass");
  expect(text).not.toContain("detector");
  expect(text).not.toContain("đo lường ai");
  // "lách" chỉ được phép xuất hiện đúng một lần trong câu phạm vi cố định.
  expect((text.match(/lách/g) ?? []).length).toBe(1);
  expect(text).toContain("không có tính năng lách kiểm duyệt");
});
