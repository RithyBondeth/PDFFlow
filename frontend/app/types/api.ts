export type JobStatus =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'expired'

export type FileFamily = 'pdf' | 'image' | 'office'

export interface UploadedFile {
  id: string
  originalName: string
  size: number
  mimeType: string
  family: FileFamily
  pageCount: number | null
  expiresAt: string
}

export interface Operation {
  key: string
  name: string
  description: string
  category: 'organize' | 'optimize' | 'edit' | 'security' | 'convert'
  accepts: FileFamily[]
  multiFile: boolean
  minFiles: number
  outputExtension: string
  implemented: boolean
  optionsSchema: Record<string, unknown>
}

export interface UploadResponse {
  files: UploadedFile[]
  availableOperations: Operation[]
}

export interface Job {
  id: string
  operation: string
  status: JobStatus
  progress: number
  stage: string | null
  errorMessage: string | null
  inputFilename: string | null
  outputFilename: string | null
  outputSize: number | null
  createdAt: string
  completedAt: string | null
  expiresAt: string
}

export interface ApiError {
  error: { code: string; message: string; requestId: string | null }
}
