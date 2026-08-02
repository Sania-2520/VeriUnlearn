"use client"

import { UploadDataset } from "@/components/workflows/upload-dataset"
import { PageHeader } from "@/components/ui/page-header"

export default function UploadDatasetPage() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Upload Dataset"
        description="Upload a new dataset to the VeriUnlearn platform through a guided workflow."
        breadcrumb={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Datasets", href: "/dashboard/datasets" },
          { label: "Upload" },
        ]}
      />
      <UploadDataset />
    </div>
  )
}
