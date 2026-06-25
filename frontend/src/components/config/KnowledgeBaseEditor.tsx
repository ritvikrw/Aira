'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Trash2, Upload, FileText, FileSpreadsheet, X, AlertCircle, Globe, Loader2, StickyNote, CheckCircle, Eye, Languages } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const LANGUAGES = [
  { code: 'hi', name: 'Hindi' },
  { code: 'te', name: 'Telugu' },
  { code: 'ta', name: 'Tamil' },
  { code: 'kn', name: 'Kannada' },
  { code: 'ml', name: 'Malayalam' },
  { code: 'mr', name: 'Marathi' },
  { code: 'bn', name: 'Bengali' },
  { code: 'gu', name: 'Gujarati' },
  { code: 'fr', name: 'French' },
  { code: 'de', name: 'German' },
  { code: 'es', name: 'Spanish' },
  { code: 'ar', name: 'Arabic' },
]


interface KnowledgeDoc {
  doc_id: string
  filename: string
  file_type: string
  chunk_count: number | null
  status: string
  created_at: string
}

export function KnowledgeBaseEditor() {
  const [files, setFiles] = useState<KnowledgeDoc[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [websiteUrl, setWebsiteUrl] = useState('')
  const [crawling, setCrawling] = useState(false)
  const [crawlError, setCrawlError] = useState<string | null>(null)
  const [noteTitle, setNoteTitle] = useState('')
  const [noteContent, setNoteContent] = useState('')
  const [savingNote, setSavingNote] = useState(false)
  const [noteSaved, setNoteSaved] = useState(false)
  const [noteError, setNoteError] = useState<string | null>(null)
  const [modalDoc, setModalDoc] = useState<KnowledgeDoc | null>(null)
  const [docContent, setDocContent] = useState<Record<string, string>>({})
  const [loadingContent, setLoadingContent] = useState<string | null>(null)
  const [translateLang, setTranslateLang] = useState<Record<string, string>>({})
  const [translatingToKb, setTranslatingToKb] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API}/knowledge-base/documents`)
        if (res.ok) setFiles(await res.json())
      } catch {
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // Poll every 2s while any document is still processing
  useEffect(() => {
    const hasProcessing = files.some(f => f.status === 'processing')
    if (!hasProcessing) return
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API}/knowledge-base/documents`)
        if (res.ok) setFiles(await res.json())
      } catch {}
    }, 2000)
    return () => clearInterval(interval)
  }, [files])

  const handleFileUpload = async (file: File) => {
    setUploading(true)
    setUploadError(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch(`${API}/knowledge-base/upload`, { method: 'POST', body: fd })
      if (!res.ok) {
        const err = await res.json() as { detail?: string }
        throw new Error(err.detail || 'Upload failed')
      }
      const saved = await res.json() as { doc_id: string; filename: string; status: string }
      setFiles(prev => [{
        doc_id: saved.doc_id,
        filename: saved.filename,
        file_type: file.name.split('.').pop()?.toLowerCase() || 'unknown',
        chunk_count: null,
        status: saved.status,
        created_at: new Date().toISOString(),
      }, ...prev])
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const handleCrawl = async () => {
    const url = websiteUrl.trim()
    if (!url) return
    setCrawling(true)
    setCrawlError(null)
    try {
      const res = await fetch(`${API}/knowledge-base/crawl`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      })
      if (!res.ok) {
        const err = await res.json() as { detail?: string }
        throw new Error(err.detail || 'Crawl failed')
      }
      const saved = await res.json() as { doc_id: string; filename: string; status: string }
      setFiles(prev => [{
        doc_id: saved.doc_id,
        filename: saved.filename,
        file_type: 'txt',
        chunk_count: null,
        status: saved.status,
        created_at: new Date().toISOString(),
      }, ...prev])
      setWebsiteUrl('')
    } catch (err) {
      setCrawlError(err instanceof Error ? err.message : 'Crawl failed')
    } finally {
      setCrawling(false)
    }
  }

  const handleSaveNote = async () => {
    const content = noteContent.trim()
    if (!content) return
    setSavingNote(true)
    setNoteError(null)
    try {
      const res = await fetch(`${API}/knowledge-base/text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: noteTitle.trim() || 'Note', content }),
      })
      if (!res.ok) {
        const err = await res.json() as { detail?: string }
        throw new Error(err.detail || 'Save failed')
      }
      const saved = await res.json() as { doc_id: string; filename: string; status: string }
      setFiles(prev => [{
        doc_id: saved.doc_id,
        filename: saved.filename,
        file_type: 'note',
        chunk_count: null,
        status: saved.status,
        created_at: new Date().toISOString(),
      }, ...prev])
      setNoteTitle('')
      setNoteContent('')
      setNoteSaved(true)
      setTimeout(() => setNoteSaved(false), 3000)
    } catch (err) {
      setNoteError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSavingNote(false)
    }
  }

  const handleTranslateToKb = async (doc: KnowledgeDoc) => {
    const lang = translateLang[doc.doc_id] || 'hi'
    const langName = LANGUAGES.find(l => l.code === lang)?.name || lang
    setTranslatingToKb(doc.doc_id)
    try {
      const res = await fetch(`${API}/knowledge-base/documents/${doc.doc_id}/translate-to-kb`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_language: lang, language_name: langName }),
      })
      if (!res.ok) {
        const err = await res.json() as { detail?: string }
        throw new Error(err.detail || 'Translation failed')
      }
      const saved = await res.json() as { doc_id: string; filename: string; status: string }
      setFiles(prev => [{
        doc_id: saved.doc_id,
        filename: saved.filename,
        file_type: 'translated',
        chunk_count: null,
        status: saved.status,
        created_at: new Date().toISOString(),
      }, ...prev])
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Translation failed')
      setTranslatingToKb(null)
    }
  }

  const openModal = async (doc: KnowledgeDoc) => {
    if (doc.status !== 'ready') return
    setModalDoc(doc)
    if (docContent[doc.doc_id]) return
    setLoadingContent(doc.doc_id)
    try {
      const res = await fetch(`${API}/knowledge-base/documents/${doc.doc_id}/content`)
      const data = await res.json() as { chunks: string[] }
      setDocContent(prev => ({ ...prev, [doc.doc_id]: data.chunks.join('\n\n---\n\n') }))
    } catch {
    } finally {
      setLoadingContent(null)
    }
  }


  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFileUpload(file)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const deleteFile = async (docId: string) => {
    if (!confirm('Remove this file from the knowledge base?')) return
    const res = await fetch(`${API}/knowledge-base/documents/${docId}`, { method: 'DELETE' })
    if (res.ok) setFiles(prev => prev.filter(f => f.doc_id !== docId))
  }

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    } catch { return iso }
  }

  const FileIcon = ({ type }: { type: string }) => {
    if (type === 'pdf') return <FileText size={20} className="text-red-500" />
    if (type === 'note') return <StickyNote size={20} className="text-amber-500" />
    if (type === 'txt') return <Globe size={20} className="text-blue-500" />
    if (type === 'translated') return <Languages size={20} className="text-purple-500" />
    return <FileSpreadsheet size={20} className="text-green-600" />
  }

  const fileBg = (type: string) => {
    if (type === 'pdf') return 'bg-red-50'
    if (type === 'note') return 'bg-amber-50'
    if (type === 'txt') return 'bg-blue-50'
    if (type === 'translated') return 'bg-purple-50'
    return 'bg-green-50'
  }

  if (loading) {
    return <div className="flex items-center justify-center py-20 text-sm text-ink-400">Loading...</div>
  }

  return (
    <>
    <div className="flex gap-6 items-start">
    {/* Left 70% — upload section */}
    <div className="flex-[7] space-y-6">
      {/* Website URL crawl */}
      <div className="bg-white rounded-xl border border-brand-300 p-5">
        <h2 className="text-sm font-semibold text-ink-900 mb-1 flex items-center gap-2">
          <Globe size={15} className="text-accent-500" /> Website
        </h2>
        <p className="text-xs text-ink-400 mb-4">
          Paste your company website URL and we'll crawl it to build the knowledge base
        </p>
        <div className="flex gap-2">
          <input
            type="url"
            value={websiteUrl}
            onChange={e => setWebsiteUrl(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleCrawl()}
            placeholder="https://yourcompany.com"
            className="flex-1 px-3 py-2 rounded-lg border border-brand-300 text-sm text-ink-900 placeholder-ink-300 focus:outline-none focus:ring-2 focus:ring-accent-400 focus:border-transparent"
          />
          <button
            onClick={handleCrawl}
            disabled={crawling || !websiteUrl.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-accent-500 text-white rounded-lg text-sm font-medium hover:bg-accent-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {crawling ? <Loader2 size={14} className="animate-spin" /> : <Globe size={14} />}
            {crawling ? 'Crawling…' : 'Crawl'}
          </button>
        </div>
        {crawlError && (
          <div className="flex items-center gap-2 mt-3 text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">
            <AlertCircle size={13} /> {crawlError}
          </div>
        )}
      </div>

      {/* Quick notes */}
      <div className="bg-white rounded-xl border border-brand-300 p-5">
        <h2 className="text-sm font-semibold text-ink-900 mb-1 flex items-center gap-2">
          <StickyNote size={15} className="text-accent-500" /> Quick notes & instructions
        </h2>
        <p className="text-xs text-ink-400 mb-4">
          Type anything directly — staff lists, FAQs, internal notes, contact info — no file needed
        </p>
        <div className="space-y-2">
          <input
            type="text"
            value={noteTitle}
            onChange={e => setNoteTitle(e.target.value)}
            placeholder="Label (e.g. Leadership team, FAQs, Office hours)"
            className="w-full px-3 py-2 rounded-lg border border-brand-300 text-sm text-ink-900 placeholder-ink-300 focus:outline-none focus:ring-2 focus:ring-accent-400 focus:border-transparent"
          />
          <textarea
            value={noteContent}
            onChange={e => setNoteContent(e.target.value)}
            placeholder={"e.g.\nCEO: John Smith – john@company.com\nCOO: Jane Doe – jane@company.com\nCTO: Alex Lee – alex@company.com"}
            rows={5}
            className="w-full px-3 py-2 rounded-lg border border-brand-300 text-sm text-ink-900 placeholder-ink-300 focus:outline-none focus:ring-2 focus:ring-accent-400 focus:border-transparent resize-none font-mono"
          />
          {noteError && (
            <div className="flex items-center gap-2 text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">
              <AlertCircle size={13} /> {noteError}
            </div>
          )}
          <div className="flex justify-end">
            <button
              onClick={handleSaveNote}
              disabled={savingNote || !noteContent.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-accent-500 text-white rounded-lg text-sm font-medium hover:bg-accent-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {savingNote
                ? <><Loader2 size={13} className="animate-spin" /> Saving…</>
                : noteSaved
                  ? <><CheckCircle size={13} /> Saved</>
                  : 'Save to knowledge base'
              }
            </button>
          </div>
        </div>
      </div>

      {/* File upload */}
      <div>
        <div
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
            dragOver ? 'border-accent-400 bg-accent-50' : 'border-brand-300 hover:border-accent-300 hover:bg-brand-50'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.xlsx,.xls,.csv"
            className="hidden"
            onChange={e => { const f = e.target.files?.[0]; if (f) handleFileUpload(f); e.target.value = '' }}
          />
          {uploading ? (
            <div>
              <div className="w-8 h-8 border-2 border-accent-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm text-ink-500">Uploading and processing...</p>
            </div>
          ) : (
            <div>
              <Upload size={24} className="mx-auto mb-3 text-ink-300" />
              <p className="text-sm font-medium text-ink-700 mb-1">Drop a file here or click to upload</p>
              <p className="text-xs text-ink-400">Supports PDF, Excel (.xlsx), CSV &mdash; max 10 MB</p>
            </div>
          )}
        </div>

        {uploadError && (
          <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-4 py-3 mt-3 text-sm text-red-700">
            <AlertCircle size={15} />
            {uploadError}
            <button className="ml-auto" onClick={() => setUploadError(null)}><X size={14} /></button>
          </div>
        )}
      </div>

    </div>

    {/* Right 30% — document list */}
    <div className="flex-[3] sticky top-0">
      <p className="text-xs font-semibold text-ink-400 uppercase tracking-widest mb-3">
        Knowledge sources <span className="font-normal normal-case">({files.length})</span>
      </p>
      {files.length === 0 ? (
        <div className="text-center py-10 text-sm text-ink-400 border border-dashed border-brand-300 rounded-xl">
          No sources yet
        </div>
      ) : (
        <div className="space-y-2">
          {files.map(file => (
            <div key={file.doc_id} className="bg-white rounded-xl border border-brand-300 overflow-hidden">
              {/* Card header */}
              <div className="p-3 flex items-center gap-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${fileBg(file.file_type)}`}>
                  <FileIcon type={file.file_type} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-ink-900 truncate">{file.filename}</p>
                  <p className="text-xs text-ink-400 mt-0.5">
                    {file.chunk_count != null ? `${file.chunk_count} chunks` : 'Processing...'}
                    &nbsp;&middot;&nbsp;{file.file_type.toUpperCase()}
                  </p>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <Badge status={file.status} />
                  {file.status === 'ready' && (
                    <button
                      onClick={() => openModal(file)}
                      className="p-1 rounded-lg hover:bg-brand-50 text-ink-400 hover:text-ink-600 transition-colors"
                      title="View extracted text"
                    >
                      <Eye size={13} />
                    </button>
                  )}
                  <button
                    onClick={() => deleteFile(file.doc_id)}
                    className="p-1 rounded-lg hover:bg-red-50 text-ink-400 hover:text-red-600 transition-colors"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>

              {/* Translate to KB — only for ready, non-translated docs */}
              {file.status === 'ready' && file.file_type !== 'translated' && (
                <div className="px-3 pb-3 flex items-center gap-2">
                  <Languages size={12} className="text-ink-400 flex-shrink-0" />
                  <select
                    value={translateLang[file.doc_id] || 'hi'}
                    onChange={e => setTranslateLang(prev => ({ ...prev, [file.doc_id]: e.target.value }))}
                    className="text-xs border border-brand-200 rounded-lg px-2 py-1 text-ink-700 focus:outline-none focus:ring-1 focus:ring-accent-400 bg-white"
                  >
                    {LANGUAGES.map(l => (
                      <option key={l.code} value={l.code}>{l.name}</option>
                    ))}
                  </select>
                  <button
                    onClick={() => handleTranslateToKb(file)}
                    disabled={translatingToKb === file.doc_id}
                    className="flex items-center gap-1 px-2 py-1 bg-purple-500 text-white rounded-lg text-xs font-medium hover:bg-purple-600 disabled:opacity-50 transition-colors"
                  >
                    {translatingToKb === file.doc_id
                      ? <><Loader2 size={10} className="animate-spin" /> Translating…</>
                      : 'Add to KB'
                    }
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
    </div>

    {/* Content modal overlay */}
    {modalDoc && (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-black/40 backdrop-blur-sm"
        onClick={() => setModalDoc(null)}
      >
        <div
          className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col"
          onClick={e => e.stopPropagation()}
        >
          {/* Modal header */}
          <div className="flex items-center gap-3 px-6 py-4 border-b border-brand-200">
            <FileIcon type={modalDoc.file_type} />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-ink-900 truncate">{modalDoc.filename}</p>
              <p className="text-xs text-ink-400">
                {modalDoc.chunk_count} chunks &middot; {modalDoc.file_type.toUpperCase()}
              </p>
            </div>
            <button
              onClick={() => setModalDoc(null)}
              className="p-1.5 rounded-lg hover:bg-brand-100 text-ink-400 hover:text-ink-700 transition-colors"
            >
              <X size={16} />
            </button>
          </div>

          {/* Modal body */}
          <div className="flex-1 overflow-y-auto px-6 py-4">
            {loadingContent === modalDoc.doc_id ? (
              <div className="flex items-center justify-center gap-2 py-20 text-ink-400">
                <Loader2 size={18} className="animate-spin" />
                <span className="text-sm">Loading content…</span>
              </div>
            ) : (
              <pre className="text-sm text-ink-700 whitespace-pre-wrap font-mono leading-relaxed">
                {docContent[modalDoc.doc_id] || 'No content available.'}
              </pre>
            )}
          </div>
        </div>
      </div>
    )}
    </>
  )
}

export default KnowledgeBaseEditor
