"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Shield, Users, Database, Boxes, FileCheck2, KeyRound, Plus, ArrowRight } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/ui/stat";
import { Select } from "@/components/ui/select";
import { Table, THead, Th, Td, TRow } from "@/components/ui/table";
import { Spinner } from "@/components/ui/progress";
import { roleLabel, allRoles } from "@/lib/rbac";
import { timeAgo } from "@/lib/utils";

interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  permissions: string[];
}

interface Overview {
  counts: Record<string, number>;
}

interface Deployment {
  id: string;
  version: string;
  environment: string;
  status: string;
  commit_sha: string | null;
  created_at: string | null;
}

export default function AdminPage() {
  const qc = useQueryClient();
  const [notice, setNotice] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [newRole, setNewRole] = useState("viewer");

  const overview = useQuery<Overview>({
    queryKey: ["admin-overview"],
    queryFn: () => api.get("/api/v1/admin/overview"),
  });
  const users = useQuery<{ users: AdminUser[] }>({
    queryKey: ["admin-users"],
    queryFn: () => api.get("/api/v1/admin/users"),
  });
  const deployments = useQuery<{ deployments: Deployment[] }>({
    queryKey: ["admin-deployments"],
    queryFn: () => api.get("/api/v1/admin/deployments"),
  });

  const createUser = useMutation({
    mutationFn: () =>
      api.post("/api/v1/admin/users", { email, full_name: fullName, password, role: newRole }),
    onSuccess: async () => {
      setNotice("User created.");
      setEmail(""); setFullName(""); setPassword("");
      await qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (e) => setNotice(e instanceof ApiError ? e.message : "Creation failed"),
  });

  const setRole = useMutation({
    mutationFn: ({ id, role }: { id: string; role: string }) =>
      api.patch(`/api/v1/admin/users/${id}/role`, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const setActive = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      api.patch(`/api/v1/admin/users/${id}/active`, is_active),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const counts = overview.data?.counts ?? {};
  const userList = users.data?.users ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Admin Portal</h1>
          <p className="mt-1 text-sm text-slate-500">
            Platform overview, user & role management, RBAC matrix, deployment history.
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/admin/roles">
            <Button variant="outline" size="sm">RBAC matrix <ArrowRight className="ml-1 h-3.5 w-3.5" /></Button>
          </Link>
          <Link href="/monitoring">
            <Button variant="outline" size="sm">Monitoring <ArrowRight className="ml-1 h-3.5 w-3.5" /></Button>
          </Link>
        </div>
      </div>

      {notice && <div className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-4 py-3 text-sm text-cyan-200">{notice}</div>}

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Users" value={counts.users ?? 0} icon={<Users className="h-4 w-4" />} accent="text-cyan-400" />
        <StatCard label="Datasets" value={counts.datasets ?? 0} icon={<Database className="h-4 w-4" />} accent="text-violet-400" />
        <StatCard label="Models" value={counts.models ?? 0} icon={<Boxes className="h-4 w-4" />} accent="text-emerald-400" />
        <StatCard label="Certificates" value={counts.certificates ?? 0} icon={<FileCheck2 className="h-4 w-4" />} accent="text-amber-400" />
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Deletion requests" value={counts.deletion_requests ?? 0} icon={<Shield className="h-4 w-4" />} accent="text-rose-400" />
        <StatCard label="API keys" value={counts.api_keys ?? 0} icon={<KeyRound className="h-4 w-4" />} accent="text-cyan-400" />
        <StatCard label="Verification reports" value={counts.verification_reports ?? 0} icon={<FileCheck2 className="h-4 w-4" />} accent="text-violet-400" />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* create user */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>
              <span className="flex items-center gap-2"><Plus className="h-4 w-4 text-cyan-400" /> New user</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <input
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Full name"
              className="w-full rounded-lg border border-slate-700 bg-slate-900/50 px-3 py-2 text-sm text-slate-200 outline-none focus:border-cyan-400/50"
            />
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              className="w-full rounded-lg border border-slate-700 bg-slate-900/50 px-3 py-2 text-sm text-slate-200 outline-none focus:border-cyan-400/50"
            />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password (min 8)"
              className="w-full rounded-lg border border-slate-700 bg-slate-900/50 px-3 py-2 text-sm text-slate-200 outline-none focus:border-cyan-400/50"
            />
            <Select value={newRole} onChange={(e) => setNewRole(e.target.value)} className="w-full">
              {allRoles().map((r) => <option key={r} value={r}>{roleLabel(r)}</option>)}
            </Select>
            <Button className="w-full" disabled={!email || !fullName || password.length < 8} onClick={() => createUser.mutate()} loading={createUser.isPending}>
              <Plus className="h-4 w-4" /> Create
            </Button>
          </CardContent>
        </Card>

        {/* users */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Users & roles</CardTitle>
          </CardHeader>
          <CardContent>
            {users.isLoading ? (
              <div className="flex justify-center py-8"><Spinner /></div>
            ) : (
              <div className="max-h-96 space-y-2 overflow-auto">
                {userList.map((u, i) => (
                  <motion.div
                    key={u.id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: Math.min(i * 0.03, 0.4) }}
                    className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-2.5"
                  >
                    <span className={`h-2 w-2 rounded-full ${u.is_active ? "bg-emerald-400" : "bg-rose-400"}`} />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-slate-200">{u.full_name}</p>
                      <p className="truncate text-xs text-slate-500">{u.email}</p>
                    </div>
                    <Select
                      value={u.role}
                      onChange={(e) => setRole.mutate({ id: u.id, role: e.target.value })}
                      className="ml-auto w-36"
                    >
                      {allRoles().map((r) => <option key={r} value={r}>{roleLabel(r)}</option>)}
                    </Select>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setActive.mutate({ id: u.id, is_active: !u.is_active })}
                    >
                      {u.is_active ? "Deactivate" : "Activate"}
                    </Button>
                  </motion.div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* deployments */}
      <Card>
        <CardHeader>
          <CardTitle>Deployment history</CardTitle>
        </CardHeader>
        <CardContent>
          {deployments.isLoading ? (
            <div className="flex justify-center py-6"><Spinner /></div>
          ) : (deployments.data?.deployments ?? []).length === 0 ? (
            <p className="py-6 text-center text-sm text-slate-500">No deployments recorded yet (CI/CD posts these).</p>
          ) : (
            <Table>
              <THead>
                <tr>
                  <Th>Version</Th>
                  <Th>Environment</Th>
                  <Th>Status</Th>
                  <Th>Commit</Th>
                  <Th>When</Th>
                </tr>
              </THead>
              <tbody>
                {(deployments.data?.deployments ?? []).map((d) => (
                  <TRow key={d.id}>
                    <Td className="mono font-medium text-slate-100">{d.version}</Td>
                    <Td><Badge tone="slate">{d.environment}</Badge></Td>
                    <Td>
                      <Badge tone={d.status === "success" ? "emerald" : d.status === "failed" ? "rose" : "amber"}>{d.status}</Badge>
                    </Td>
                    <Td className="mono text-xs text-slate-500">{d.commit_sha ? d.commit_sha.slice(0, 8) : "—"}</Td>
                    <Td className="text-xs text-slate-500">{timeAgo(d.created_at)}</Td>
                  </TRow>
                ))}
              </tbody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
