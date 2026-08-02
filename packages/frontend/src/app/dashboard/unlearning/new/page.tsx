"use client"

import { SubmitDeletionRequest } from "@/components/workflows/submit-deletion-request"
import { PageHeader } from "@/components/ui/page-header"

export default function NewUnlearningRequestPage() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="New Deletion Request"
        description="Submit a data deletion request for the Right to be Forgotten through a guided workflow."
        breadcrumb={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Unlearning", href: "/dashboard/unlearning" },
          { label: "New Request" },
        ]}
      />
      <SubmitDeletionRequest />
    </div>
  )
}
