"use client";

import { useState } from "react";

export default function Home() {
  const [count, setCount] = useState(0);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-4xl font-bold mb-8">
        VeriUnlearn
      </h1>
      <p className="text-xl mb-4">
        Verifiable Machine Unlearning Framework
      </p>
      <p className="text-sm text-gray-500 mb-8">
        Cryptographic Proofs for GDPR-Compliant AI Systems
      </p>
      <button
        onClick={() => setCount((c) => c + 1)}
        className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition"
      >
        Count is {count}
      </button>
    </main>
  );
}
