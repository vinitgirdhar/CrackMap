import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CrackMap — Road Health Intelligence",
  description: "AI road damage and pothole detection powered by YOLOv8.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
