import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Speech to Text",
  description: "Personal speech-to-text app powered by LiveKit",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
