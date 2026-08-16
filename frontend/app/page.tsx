import Link from "next/link";
import {
  Fingerprint,
  ShieldCheck,
  Lock,
  Scale,
  FileCheck2,
  Boxes,
  Gauge,
  ArrowRight,
  ScrollText,
} from "lucide-react";
import { HeroCanvas } from "@/components/HeroCanvas";

const features = [
  {
    icon: Fingerprint,
    title: "Privacy Auditor",
    desc: "Search any identity across every model shard — embeddings, LoRA adapters, influence scores and sensitivity, with confidence scoring.",
  },
  {
    icon: Boxes,
    title: "SISA Engine",
    desc: "Sharded, isolated, sliced, aggregated training. Deleting a record retrains one shard, never the whole model.",
  },
  {
    icon: ShieldCheck,
    title: "Certified Removal",
    desc: "Newton-step removal with a provable bound on prediction drift for convex models (Guo et al., ICML 2020).",
  },
  {
    icon: FileCheck2,
    title: "Merkle Deletion Proofs",
    desc: "Pre/post dataset roots, tombstoned leaves, RSA-signed certificates with ZK-style commitments.",
  },
  {
    icon: ScrollText,
    title: "Immutable Audit Trail",
    desc: "Hash-chained event log with tamper detection — every request, certificate and verification is provable.",
  },
  {
    icon: Scale,
    title: "GDPR & DPDP",
    desc: "Right-to-be-forgotten (Art. 17) and DPDP Act 2023 workflows with live compliance scoring.",
  },
];

export default function LandingPage() {
  return (
    <main className="relative min-h-screen overflow-hidden cyber-grid">
      <HeroCanvas />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-[#05070d]" />

      <nav className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2">
          <Lock className="h-6 w-6 text-cyan-400" />
          <span className="text-lg font-bold tracking-tight">
            Veri<span className="text-cyan-400">Unlearn</span>
          </span>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/login">
            <span className="rounded-lg px-4 py-2 text-sm text-slate-300 transition-colors hover:bg-slate-800/60">
              Sign in
            </span>
          </Link>
          <Link href="/register">
            <span className="rounded-lg bg-cyan-500/90 px-4 py-2 text-sm font-semibold text-slate-950 shadow-[0_0_20px_-4px_rgba(34,211,238,0.7)] transition-all hover:bg-cyan-400">
              Get started
            </span>
          </Link>
        </div>
      </nav>

      <section className="relative z-10 mx-auto max-w-5xl px-6 pb-24 pt-16 text-center">
        <div className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-4 py-1.5 text-xs font-medium text-cyan-300">
          <ShieldCheck className="h-3.5 w-3.5" />
          Verifiable Machine Unlearning Framework
        </div>
        <h1 className="text-glow mx-auto max-w-3xl text-5xl font-extrabold leading-tight tracking-tight md:text-6xl">
          Make AI <span className="bg-gradient-to-r from-cyan-400 to-violet-400 bg-clip-text text-transparent">forget</span>,
          <br />
          and prove it.
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-400">
          Selectively remove user data from trained models with cryptographic proof of deletion —
          SISA, influence functions, certified removal, Merkle-tree certificates and an immutable
          audit trail for GDPR Article 17 and DPDP Act 2023 compliance.
        </p>
        <div className="mt-10 flex items-center justify-center gap-4">
          <Link href="/register">
            <span className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-6 py-3.5 font-semibold text-slate-950 shadow-[0_0_30px_-6px_rgba(34,211,238,0.8)] transition-all hover:bg-cyan-400">
              Launch the platform <ArrowRight className="h-4 w-4" />
            </span>
          </Link>
          <Link href="/login">
            <span className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-6 py-3.5 font-medium text-slate-200 transition-colors hover:bg-slate-800/60">
              <Gauge className="h-4 w-4" /> Demo dashboard
            </span>
          </Link>
        </div>
      </section>

      <section className="relative z-10 mx-auto max-w-6xl px-6 pb-24">
        <div className="grid gap-5 md:grid-cols-3">
          {features.map((f) => (
            <div
              key={f.title}
              className="glass group p-6 transition-all duration-300 hover:border-cyan-500/40 hover:shadow-[0_0_30px_-8px_rgba(34,211,238,0.4)]"
            >
              <f.icon className="mb-4 h-7 w-7 text-cyan-400 transition-transform group-hover:scale-110" />
              <h3 className="mb-2 font-semibold text-slate-100">{f.title}</h3>
              <p className="text-sm leading-relaxed text-slate-400">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="relative z-10 border-t border-slate-800/60 py-8 text-center text-xs text-slate-600">
        VeriUnlearn · Verifiable Machine Unlearning · GDPR Art. 17 · DPDP Act 2023
      </footer>
    </main>
  );
}
