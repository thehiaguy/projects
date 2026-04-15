import "./globals.css";

export const metadata = {
  title: "Empathic AI Therapy Frontend",
  description: "Frontend control room for voice, transcript, graph, and receipts",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
