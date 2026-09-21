import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GenLayer AI Dispute Resolver — Decentralized Escrow Adjudication",
  description:
    "Decentralized freelance milestone escrow and AI-powered dispute adjudication built on GenLayer Intelligent Contracts.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
