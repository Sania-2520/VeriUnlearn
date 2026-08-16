"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, statusTone } from "@/components/ui/badge";
import { Table, THead, Th, Td, TRow } from "@/components/ui/table";
import { Spinner } from "@/components/ui/progress";
import { timeAgo } from "@/lib/utils";

interface Certificate {
  id: string;
  subject_user_id: string;
  deletion_type: string;
  deleted_record_count: number;
  model_version: number;
  shard_ids: number[];
  pre_merkle_root: string;
  post_merkle_root: string;
  method: string;
  certified_bound: number | null;
  timestamp: string;
  verification_status: string;
  blockchain_tx: string | null;
  created_at: string | null;
}

export default function CertificatesPage() {
  const { data, isLoading } = useQuery<Certificate[]>({
    queryKey: ["certificates"],
    queryFn: () => api.get("/api/v1/certificates?limit=100"),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Deletion Certificates</h1>
        <p className="mt-1 text-sm text-slate-500">
          RSA-signed certificates binding pre/post Merkle roots, model state and deleted records.
        </p>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner className="h-8 w-8" /></div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Issued certificates</CardTitle>
            <Badge tone="cyan">{data?.length ?? 0} total</Badge>
          </CardHeader>
          <Table>
            <THead>
              <tr>
                <Th>ID</Th>
                <Th>Subject</Th>
                <Th>Type / Method</Th>
                <Th>Records</Th>
                <Th>Shards</Th>
                <Th>Merkle transition</Th>
                <Th>Status</Th>
                <Th>Issued</Th>
                <Th></Th>
              </tr>
            </THead>
            <tbody>
              {(data ?? []).map((c) => (
                <TRow key={c.id}>
                  <Td className="mono text-xs text-cyan-300">{c.id.slice(0, 10)}</Td>
                  <Td>{c.subject_user_id}</Td>
                  <Td>
                    <div>{c.deletion_type}</div>
                    <div className="mono text-xs text-slate-500">{c.method}</div>
                  </Td>
                  <Td className="mono">{c.deleted_record_count}</Td>
                  <Td className="mono text-xs">{c.shard_ids.join(", ") || "—"}</Td>
                  <Td className="mono max-w-[220px] truncate text-xs">
                    <span className="text-slate-500">{c.pre_merkle_root.slice(0, 10)}</span>
                    <span className="text-cyan-500"> → </span>
                    <span className="text-cyan-300">{c.post_merkle_root.slice(0, 10)}</span>
                  </Td>
                  <Td>
                    <Badge tone={statusTone(c.verification_status)}>{c.verification_status}</Badge>
                    {c.blockchain_tx && <div className="mt-1 text-[10px] text-violet-300">on-chain</div>}
                  </Td>
                  <Td className="text-xs text-slate-500">{timeAgo(c.created_at)}</Td>
                  <Td>
                    <Link href={`/certificates/${c.id}`}>
                      <span className="inline-flex items-center gap-1 text-sm text-cyan-400 hover:underline">
                        Open <ArrowRight className="h-3.5 w-3.5" />
                      </span>
                    </Link>
                  </Td>
                </TRow>
              ))}
              {(data ?? []).length === 0 && (
                <TRow>
                  <Td colSpan={9} className="py-10 text-center text-slate-500">
                    No certificates yet. Run a deletion from the Privacy Auditor to mint one.
                  </Td>
                </TRow>
              )}
            </tbody>
          </Table>
        </Card>
      )}
    </div>
  );
}
