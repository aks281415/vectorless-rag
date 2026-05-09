import "./globals.css";

export const metadata = {
  title: "Vectorless RAG — Chat with your Documents",
  description:
    "Upload PDFs and chat with them using reasoning-based, vectorless retrieval powered by PageIndex and DeepSeek.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <div className="bg-gradient" />
        {children}
      </body>
    </html>
  );
}
