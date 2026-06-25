'use client'

import { useEffect, useRef, useState } from 'react'
import { Upload, Trash2, FileText, FileSpreadsheet, Loader2, AlertCircle } from 'lucide-react'
import { format } from 'date-fns'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface KnowledgeDoc {
  doc_id: string
  filename: string
  file_type: string
  chunk_count: number
  status: 'processing' | 'ready' | 'error'
  created_at: string
  error_msg?: string | null
}

export default function KnowledgeBaseManager() {
  const [docs, setDocs] = useState<KnowledgeDoc[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const fetchDocs = () => {
    fetch(`${API}/knowledge-base/documents`)
      .then(r => r.json())
      .then(setDocs)
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchDocs() }, [])

  // Poll for processing docs
  useEffect(() => {
    const hasProcessing = docs.some(d => d.status === 'processing')
    if (!hasProcessing) return
    const t = setInterval(fetchDocs, 3000)
    return () => clearInterval(t)
  }, [docs])

  const upload = async (file: File) => {
    setUploading(true)
    const form = new FormData()
    form.append('file', file)
    try {
      await fetch(`${API}/knowledge-base/upload`, { method: 'POST', body: form })
      fetchDocs()
      setUploading(false)
    }
  }

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return
    upload(files[0])
  }

  const handleDelete = async (docId: string) => {
    setDeletingId(docId)
    try {
      await fetch(`${API}/knowledge-base/documents/${docId}`, { method: 'DELETE' })
      setDocs(prev => prev.filter(d => d.doc_id !== docId))
      setDeletingId(null)
    }
  }

  const FileIcon = ({ type }: { type: string }) =>
    type === 'pdf'
      ? <FileText className="w-5 h-5 text-red-500" />
      : <FileSpreadsheet className="w-5 h-5 text-green-600" />

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      {/* Upload zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={e => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files) }}
        className={`border-2 border-dashed rounded-xl p-10 text-center transition-all cursor-pointer ${
          dragOver ? 'border-accent-400 bg-accent-50' : 'border-brand-300 hover:border-accent-300 hover:bg-brand-50'
        }`}
        onClick={() => fileRef.current?.click()}
      >
        <input
          ref={fileRef}
          type="file"
          className="hidden"
          accept=".pdf,.xlsx,.xls,.csv"
          onChange={e => handleFiles(e.target.files)}
        />
        {uploading ? (
          <div className="flex flex-col items-center gap-2 text-ink-500">
            <Loader2 className="w-8 h-8 animate-spin text-accent-500" />
            <p className="text-sm font-medium">Uploading and processing…</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <Upload className="w-8 h-8 text-brand-400" />
            <p className="text-sm font-medium text-ink-700">Drop a file here or click to browse</p>
            <p className="text-xs text-ink-400">Supported: PDF, XLSX, XLS, CSV</p>
          </div>
        )}
      </div>

      {/* Document list */}
      <div>
        <h2 className="text-sm font-semibold text-ink-900 mb-3">
          Documents <span className="text-ink-400 font-normal">({docs.length})</span>
        </h2>

        {loading ? (
          <div className="flex items-center gap-2 text-ink-400 py-8 justify-center">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading…
          </div>
        ) : docs.length === 0 ? (
          <div className="text-center py-12 border border-dashed border-brand-300 rounded-xl">
            <FileText className="w-8 h-8 text-brand-400 mx-auto mb-2" />
            <p className="text-sm text-ink-500">No documents uploaded yet</p>
            <p className="text-xs text-ink-400 mt-1">Upload a PDF or Excel file to build the knowledge base</p>
          </div>
        ) : (
          <div className="space-y-2">
            {docs.map(doc => (
              <div key={doc.doc_id} className="bg-white border border-brand-300 rounded-xl px-4 py-3 flex items-center gap-3">
                <FileIcon type={doc.file_type} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-ink-900 truncate">{doc.filename}</p>
                  <div className="flex items-center gap-3 mt-0.5">
                    <span className="text-xs text-ink-400">
                      {doc.chunk_count > 0 ? `${doc.chunk_count} chunks` : doc.file_type.toUpperCase()}
                    </span>
                    <span className="text-xs text-ink-400">
                      {format(new Date(doc.created_at), 'MMM d, h:mm a')}
                    </span>
                    {doc.status === 'error' && doc.error_msg && (
                      <span className="flex items-center gap-1 text-xs text-red-500">
                        <AlertCircle className="w-3 h-3" /> {doc.error_msg.slice(0, 40)}
                      </span>
                    )}
                  </div>
                </div>
                <Badge status={doc.status} />
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDelete(doc.doc_id)}
                  disabled={deletingId === doc.doc_id}
                  className="text-red-500 hover:bg-red-50 hover:text-red-600 shrink-0"
                >
                  {deletingId === doc.doc_id
                    ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    : <Trash2 className="w-3.5 h-3.5" />}
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
