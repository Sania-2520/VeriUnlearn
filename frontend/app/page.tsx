import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="max-w-2xl text-center space-y-8">
        <div className="space-y-2">
          <h1 className="text-5xl font-bold tracking-tight text-gray-900">
            VeriUnlearn{" "}
            <span className="text-primary-600">Pro</span>
          </h1>
          <p className="text-xl text-gray-500">
            Verifiable Machine Unlearning for Privacy-Preserving AI
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4 max-w-lg mx-auto">
          <Link
            href="/login"
            className="rounded-lg bg-primary-600 px-6 py-3 text-white font-medium hover:bg-primary-700 transition-colors"
          >
            Sign In
          </Link>
          <Link
            href="/register"
            className="rounded-lg border border-gray-300 px-6 py-3 text-gray-700 font-medium hover:bg-gray-50 transition-colors"
          >
            Register
          </Link>
        </div>

        <div className="grid grid-cols-3 gap-6 text-sm text-gray-500 mt-12">
          <div className="space-y-2">
            <div className="text-2xl font-bold text-gray-900">SISA</div>
            <p>Sharded training for efficient unlearning</p>
          </div>
          <div className="space-y-2">
            <div className="text-2xl font-bold text-gray-900">MIA</div>
            <p>Membership inference verification</p>
          </div>
          <div className="space-y-2">
            <div className="text-2xl font-bold text-gray-900">Ed25519</div>
            <p>Cryptographic proof certificates</p>
          </div>
        </div>
      </div>
    </main>
  );
}
