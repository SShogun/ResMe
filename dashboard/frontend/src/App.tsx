import React, { useState, useEffect } from 'react'
import { 
  LayoutDashboard, Sparkles, FileJson, Calendar, ArrowRight, Plus, 
  Trash2, Copy, Check, FileText, CheckCircle2, AlertCircle, Save, Loader2, ListTodo
} from 'lucide-react'

const getApiBase = () => {
  const host = import.meta.env.VITE_API_HOST
  if (host) {
    if (host.startsWith('http://') || host.startsWith('https://')) {
      return host.endsWith('/api') ? host : `${host}/api`
    }
    return `https://${host}/api`
  }
  return import.meta.env.VITE_API_BASE || "http://localhost:8000/api"
}
const API_BASE = getApiBase()

export default function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'tailor' | 'resume'>('dashboard')
  const [applications, setApplications] = useState<any[]>([])
  const [resumeData, setResumeData] = useState<any>(null)
  const [stats, setStats] = useState<any>({
    total_applications: 0,
    by_status: { Wishlist: 0, Applied: 0, Interviewing: 0, Offer: 0, Rejected: 0 },
    interview_rate: 0.0,
    offer_rate: 0.0
  })

  // Tailor Tab State
  const [jobDescription, setJobDescription] = useState('')
  const [selectedProjects, setSelectedProjects] = useState<string[]>([])
  const [isTailoring, setIsTailoring] = useState(false)
  const [tailorResult, setTailorResult] = useState<any>(null)
  const [tailorError, setTailorError] = useState('')
  const [copied, setCopied] = useState(false)
  const [saveToAppCompany, setSaveToAppCompany] = useState('')
  const [saveToAppTitle, setSaveToAppTitle] = useState('')
  const [isSavingTailoredApp, setIsSavingTailoredApp] = useState(false)

  // Modals & Edits
  const [showAddModal, setShowAddModal] = useState(false)
  const [newApp, setNewApp] = useState({
    company: '', title: '', status: 'Applied', 
    date_applied: new Date().toISOString().split('T')[0], 
    notes: '', jd_text: '', latex_content: ''
  })
  
  const [selectedApp, setSelectedApp] = useState<any>(null)
  const [isEditingResume, setIsEditingResume] = useState(false)
  const [editedResume, setEditedResume] = useState<any>(null)

  useEffect(() => {
    fetchApplications()
    fetchResume()
    fetchStats()
  }, [])

  const fetchApplications = async () => {
    try {
      const res = await fetch(`${API_BASE}/applications`)
      if (res.ok) setApplications(await res.json())
    } catch (err) { console.error("Error fetching applications:", err) }
  }

  const fetchResume = async () => {
    try {
      const res = await fetch(`${API_BASE}/resume`)
      if (res.ok) {
        const data = await res.json()
        setResumeData(data)
        setEditedResume(data)
        if (data.projects) setSelectedProjects(data.projects.map((p: any) => p.title))
      }
    } catch (err) { console.error("Error fetching resume:", err) }
  }

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/stats`)
      if (res.ok) setStats(await res.json())
    } catch (err) { console.error("Error fetching stats:", err) }
  }

  const handleCreateApplication = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newApp.company || !newApp.title) return
    try {
      const res = await fetch(`${API_BASE}/applications`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newApp)
      })
      if (res.ok) {
        setShowAddModal(false)
        setNewApp({ ...newApp, company: '', title: '', notes: '', jd_text: '', latex_content: '' })
        fetchApplications()
        fetchStats()
      }
    } catch (err) { console.error("Error creating application:", err) }
  }

  const handleDeleteApplication = async (appId: number) => {
    if (!confirm("Are you sure you want to delete this application?")) return
    try {
      const res = await fetch(`${API_BASE}/applications/${appId}`, { method: 'DELETE' })
      if (res.ok) {
        setSelectedApp(null)
        fetchApplications()
        fetchStats()
      }
    } catch (err) { console.error("Error deleting application:", err) }
  }

  const handleUpdateApplicationDetails = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedApp) return
    try {
      const res = await fetch(`${API_BASE}/applications/${selectedApp.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(selectedApp)
      })
      if (res.ok) {
        fetchApplications()
        fetchStats()
      }
    } catch (err) { console.error("Error updating details:", err) }
  }

  const handleSaveResume = async () => {
    try {
      const res = await fetch(`${API_BASE}/resume`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editedResume)
      })
      if (res.ok) {
        setResumeData(editedResume)
        setIsEditingResume(false)
      }
    } catch (err) { alert("Failed to save resume.") }
  }

  const handleTailorSubmit = async () => {
    if (!jobDescription.trim()) {
      setTailorError("Please paste a target Job Description first.")
      return
    }
    setTailorError("")
    setIsTailoring(true)
    setTailorResult(null)

    try {
      const res = await fetch(`${API_BASE}/tailor`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_description: jobDescription, selected_projects: selectedProjects })
      })
      if (res.ok) {
        const data = await res.json()
        setTailorResult(data)
        const jdFirstLine = jobDescription.split('\n')[0]
        setSaveToAppCompany(jdFirstLine.substring(0, 20) || "Target Company")
        setSaveToAppTitle("Software Engineer")
      } else {
        const errData = await res.json()
        setTailorError(errData.detail || "Tailoring engine failed to customize.")
      }
    } catch (err) {
      setTailorError("Server offline or rate limits hit.")
    } finally {
      setIsTailoring(false)
    }
  }

  const handleQuickSaveTailoredApp = async () => {
    if (!saveToAppCompany || !saveToAppTitle || !tailorResult) return
    setIsSavingTailoredApp(true)
    try {
      const res = await fetch(`${API_BASE}/applications`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company: saveToAppCompany, title: saveToAppTitle, status: 'Applied',
          date_applied: new Date().toISOString().split('T')[0],
          notes: `Auto-generated using AI tailoring.`, jd_text: jobDescription,
          latex_content: tailorResult.latex_content
        })
      })
      if (res.ok) {
        fetchApplications()
        fetchStats()
        setActiveTab('dashboard')
        setTailorResult(null)
        setJobDescription('')
      }
    } catch (err) { console.error(err) } 
    finally { setIsSavingTailoredApp(false) }
  }

  const copyToClipboard = () => {
    if (!tailorResult) return
    navigator.clipboard.writeText(tailorResult.latex_content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const downloadLaTeXFile = () => {
    if (!tailorResult) return
    const blob = new Blob([tailorResult.latex_content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `Soham_Shirke_${saveToAppCompany.replace(/\s+/g, '_') || 'Tailored'}.tex`
    link.click()
    URL.revokeObjectURL(url)
  }

  const toggleProjectSelection = (title: string) => {
    if (selectedProjects.includes(title)) setSelectedProjects(selectedProjects.filter(t => t !== title))
    else setSelectedProjects([...selectedProjects, title])
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* HEADER */}
      <header style={{ 
        padding: '20px 32px', 
        borderBottom: '1px solid var(--border)', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        background: 'var(--surface-0)',
        position: 'sticky',
        top: 0,
        zIndex: 50
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ background: 'var(--accent)', padding: '8px', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Sparkles size={20} color="#fff" />
          </div>
          <div>
            <h1 style={{ fontSize: '18px', margin: 0, color: '#fff' }}>ResMe</h1>
            <p style={{ fontSize: '12px', margin: 0, color: 'var(--text-tertiary)' }}>Career CRM & Resume AI</p>
          </div>
        </div>

        <nav style={{ display: 'flex', gap: '4px', background: 'var(--surface-1)', padding: '4px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
          <button className={`nav-pill ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
            <LayoutDashboard size={16} /> Kanban Board
          </button>
          <button className={`nav-pill ${activeTab === 'tailor' ? 'active' : ''}`} onClick={() => setActiveTab('tailor')}>
            <Sparkles size={16} /> AI Customizer
          </button>
          <button className={`nav-pill ${activeTab === 'resume' ? 'active' : ''}`} onClick={() => setActiveTab('resume')}>
            <FileJson size={16} /> Master JSON
          </button>
        </nav>
      </header>

      <main style={{ flex: 1, padding: '32px', maxWidth: '1400px', margin: '0 auto', width: '100%' }}>
        
        {/* --- DASHBOARD TAB --- */}
        {activeTab === 'dashboard' && (
          <div className="anim-fade-in stagger">
            
            {/* STATS */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '32px' }}>
              <div className="stat-card">
                <div className="stat-label">Total Applied</div>
                <div className="stat-value text-primary">{stats.total_applications}</div>
              </div>
              <div className="stat-card" style={{ '--stat-accent': 'var(--yellow)' } as any}>
                <div className="stat-label">Interviewing</div>
                <div className="stat-value" style={{ color: 'var(--yellow)' }}>{stats.by_status.Interviewing}</div>
              </div>
              <div className="stat-card" style={{ '--stat-accent': 'var(--green)' } as any}>
                <div className="stat-label">Offers</div>
                <div className="stat-value" style={{ color: 'var(--green)' }}>{stats.by_status.Offer}</div>
              </div>
              <div className="stat-card" style={{ '--stat-accent': 'var(--blue)' } as any}>
                <div className="stat-label">Interview Rate</div>
                <div className="stat-value" style={{ color: 'var(--blue)' }}>{stats.interview_rate}%</div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '24px', alignItems: 'flex-start' }}>
              {/* KANBAN BOARD */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h2 style={{ fontSize: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <ListTodo size={18} color="var(--accent)" /> Pipeline
                  </h2>
                  <button className="btn-primary" onClick={() => setShowAddModal(true)}>
                    <Plus size={16} /> Add Application
                  </button>
                </div>
                
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '12px' }}>
                  {(['Wishlist', 'Applied', 'Interviewing', 'Offer', 'Rejected'] as const).map(col => {
                    const colApps = applications.filter(a => a.status === col)
                    return (
                      <div key={col} className="kanban-col">
                        <div className="kanban-col-header">
                          <span className="col-title">{col}</span>
                          <span className="col-count">{colApps.length}</span>
                        </div>
                        <div className="kanban-col-body">
                          {colApps.map(app => (
                            <div 
                              key={app.id} 
                              className="app-card"
                              style={{ 
                                '--card-accent': `var(--color-${col.toLowerCase()})`,
                                borderColor: selectedApp?.id === app.id ? 'var(--accent)' : 'var(--border)'
                              } as any}
                              onClick={() => setSelectedApp(app)}
                            >
                              <div className="app-company">{app.company}</div>
                              <div className="app-role">{app.title}</div>
                              <div className="app-date"><Calendar size={12} /> {app.date_applied}</div>
                            </div>
                          ))}
                          {colApps.length === 0 && <div className="empty-state" style={{ padding: '20px 0', border: 'none' }}>No jobs here</div>}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* DETAILS DRAWER */}
              {selectedApp && (
                <div className="detail-panel" style={{ width: '380px', flexShrink: 0, position: 'sticky', top: '100px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
                    <div>
                      <h3 style={{ fontSize: '18px', color: '#fff', marginBottom: '4px' }}>{selectedApp.company}</h3>
                      <p style={{ fontSize: '13px', color: 'var(--text-tertiary)' }}>{selectedApp.title}</p>
                    </div>
                    <button className="btn-ghost" style={{ padding: '4px 8px' }} onClick={() => setSelectedApp(null)}>✕</button>
                  </div>
                  
                  <form onSubmit={handleUpdateApplicationDetails} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div>
                      <label className="section-label">Status</label>
                      <select value={selectedApp.status} onChange={(e) => setSelectedApp({...selectedApp, status: e.target.value})}>
                        <option value="Wishlist">Wishlist</option>
                        <option value="Applied">Applied</option>
                        <option value="Interviewing">Interviewing</option>
                        <option value="Offer">Offer</option>
                        <option value="Rejected">Rejected</option>
                      </select>
                    </div>
                    <div>
                      <label className="section-label">Date Applied</label>
                      <input type="date" value={selectedApp.date_applied} onChange={(e) => setSelectedApp({...selectedApp, date_applied: e.target.value})} />
                    </div>
                    <div>
                      <label className="section-label">Notes</label>
                      <textarea rows={4} value={selectedApp.notes || ''} onChange={(e) => setSelectedApp({...selectedApp, notes: e.target.value})} placeholder="Interview notes..." />
                    </div>
                    <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                      <button type="submit" className="btn-primary" style={{ flex: 1 }}><Save size={14} /> Update</button>
                      <button type="button" className="btn-ghost" onClick={() => handleDeleteApplication(selectedApp.id)} style={{ color: 'var(--red)', borderColor: 'rgba(248, 113, 113, 0.2)' }}><Trash2 size={14} /></button>
                    </div>
                  </form>
                  
                  {selectedApp.latex_content && (
                    <div style={{ marginTop: '24px', padding: '16px', background: 'var(--accent-bg)', border: '1px solid var(--accent-border)', borderRadius: 'var(--radius-md)' }}>
                      <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                        <FileText size={14} /> Tailored Resume Attached
                      </div>
                      <button className="btn-ghost" style={{ width: '100%', fontSize: '12px' }} onClick={() => {
                        navigator.clipboard.writeText(selectedApp.latex_content)
                        alert("LaTeX copied!")
                      }}>Copy .tex Source</button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* --- AI CUSTOMIZER TAB --- */}
        {activeTab === 'tailor' && (
          <div className="anim-fade-in stagger" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '32px', alignItems: 'start' }}>
            
            {/* Input Form */}
            <div className="card-elevated" style={{ padding: '24px' }}>
              <div className="section-label">Target Job Description</div>
              <textarea 
                rows={12} 
                value={jobDescription} 
                onChange={(e) => setJobDescription(e.target.value)} 
                placeholder="Paste JD from LinkedIn, Wellfound, etc."
                style={{ marginBottom: '24px' }}
              />

              {resumeData && resumeData.projects && (
                <div style={{ marginBottom: '24px' }}>
                  <div className="section-label">Select Projects to Tailor</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {resumeData.projects.map((p: any) => (
                      <label key={p.title} className="project-check">
                        <input type="checkbox" checked={selectedProjects.includes(p.title)} onChange={() => toggleProjectSelection(p.title)} />
                        <span>{p.title}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {tailorError && (
                <div style={{ padding: '12px', background: 'var(--red-dim)', color: 'var(--red)', borderRadius: 'var(--radius-sm)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px' }}>
                  <AlertCircle size={14} /> {tailorError}
                </div>
              )}

              <button className="btn-primary" style={{ width: '100%', padding: '14px' }} onClick={handleTailorSubmit} disabled={isTailoring}>
                {isTailoring ? <><Loader2 size={16} className="anim-spin" /> Customizing...</> : <><Sparkles size={16} /> Generate Tailored Resume</>}
              </button>
            </div>

            {/* Results Output */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              
              {!isTailoring && !tailorResult && (
                <div className="empty-state" style={{ minHeight: '400px' }}>
                  <Sparkles size={32} style={{ marginBottom: '16px', opacity: 0.5 }} />
                  <p>Paste a JD and click generate to see the AI magic.</p>
                </div>
              )}

              {isTailoring && (
                <div className="empty-state" style={{ minHeight: '400px' }}>
                  <Loader2 size={32} className="anim-spin" style={{ color: 'var(--accent)', marginBottom: '16px' }} />
                  <p>Analyzing JD and rewriting bullet points...</p>
                </div>
              )}

              {tailorResult && (
                <>
                  <div className="card-elevated" style={{ padding: '24px' }}>
                    <div className="section-label">Modifications (Diff)</div>
                    {tailorResult.modifications.length === 0 ? (
                      <p style={{ fontSize: '13px', color: 'var(--text-tertiary)' }}>No changes needed.</p>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxHeight: '400px', overflowY: 'auto' }}>
                        {tailorResult.modifications.map((mod: any) => (
                          <div key={mod.project_title}>
                            <h4 style={{ fontSize: '13px', color: '#fff', marginBottom: '8px' }}>{mod.project_title}</h4>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                              {mod.bullets.map((b: any, i: number) => (
                                <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                                  <div className="diff-old">{b.old}</div>
                                  <div className="diff-new">{b.new}</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="card-elevated" style={{ padding: '24px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                      <div className="section-label" style={{ margin: 0 }}>LaTeX Source</div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button className="btn-ghost" onClick={copyToClipboard}>
                          {copied ? <Check size={14} color="var(--green)" /> : <Copy size={14} />} Copy
                        </button>
                        <button className="btn-ghost" onClick={downloadLaTeXFile}>Download</button>
                      </div>
                    </div>
                    <div className="code-block">{tailorResult.latex_content}</div>
                  </div>

                  <div className="card-elevated" style={{ padding: '24px', background: 'var(--accent-bg)', borderColor: 'var(--accent-border)' }}>
                    <div className="section-label">Quick Save to Kanban</div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
                      <input type="text" placeholder="Company" value={saveToAppCompany} onChange={e => setSaveToAppCompany(e.target.value)} />
                      <input type="text" placeholder="Title" value={saveToAppTitle} onChange={e => setSaveToAppTitle(e.target.value)} />
                    </div>
                    <button className="btn-primary" style={{ width: '100%' }} onClick={handleQuickSaveTailoredApp} disabled={isSavingTailoredApp}>
                      {isSavingTailoredApp ? 'Saving...' : 'Link Resume & Track Application'}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* --- MASTER RESUME JSON EDITOR --- */}
        {activeTab === 'resume' && resumeData && editedResume && (
          <div className="anim-fade-in stagger card-elevated" style={{ padding: '32px', maxWidth: '800px', margin: '0 auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
              <div>
                <h2 style={{ fontSize: '20px', color: '#fff', marginBottom: '4px' }}>Master Profile</h2>
                <p style={{ fontSize: '13px', color: 'var(--text-tertiary)' }}>This serves as the base context for AI generation.</p>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                {isEditingResume ? (
                  <>
                    <button className="btn-ghost" onClick={() => { setEditedResume(JSON.parse(JSON.stringify(resumeData))); setIsEditingResume(false); }}>Cancel</button>
                    <button className="btn-primary" onClick={handleSaveResume}><Save size={14} /> Save Changes</button>
                  </>
                ) : (
                  <button className="btn-primary" onClick={() => setIsEditingResume(true)}>Edit JSON Config</button>
                )}
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
              {/* Meta */}
              <div>
                <div className="section-label">Metadata</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <input disabled={!isEditingResume} value={editedResume.meta.name} onChange={e => setEditedResume({...editedResume, meta: {...editedResume.meta, name: e.target.value}})} placeholder="Name" />
                  <input disabled={!isEditingResume} value={editedResume.meta.email} onChange={e => setEditedResume({...editedResume, meta: {...editedResume.meta, email: e.target.value}})} placeholder="Email" />
                  <input disabled={!isEditingResume} value={editedResume.meta.phone} onChange={e => setEditedResume({...editedResume, meta: {...editedResume.meta, phone: e.target.value}})} placeholder="Phone" />
                  <input disabled={!isEditingResume} value={editedResume.meta.linkedin} onChange={e => setEditedResume({...editedResume, meta: {...editedResume.meta, linkedin: e.target.value}})} placeholder="LinkedIn" />
                </div>
              </div>

              {/* Skills */}
              <div>
                <div className="section-label">Technical Skills</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <input disabled={!isEditingResume} value={editedResume.technical_skills.languages.join(", ")} onChange={e => setEditedResume({...editedResume, technical_skills: {...editedResume.technical_skills, languages: e.target.value.split(',').map(s=>s.trim())}})} placeholder="Languages" />
                  <input disabled={!isEditingResume} value={editedResume.technical_skills.backend.join(", ")} onChange={e => setEditedResume({...editedResume, technical_skills: {...editedResume.technical_skills, backend: e.target.value.split(',').map(s=>s.trim())}})} placeholder="Backend" />
                  <input disabled={!isEditingResume} value={editedResume.technical_skills.tools.join(", ")} onChange={e => setEditedResume({...editedResume, technical_skills: {...editedResume.technical_skills, tools: e.target.value.split(',').map(s=>s.trim())}})} placeholder="Tools" />
                </div>
              </div>
            </div>
          </div>
        )}

      </main>

      {/* --- ADD MODAL --- */}
      {showAddModal && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <h3 style={{ fontSize: '18px', color: '#fff', marginBottom: '24px' }}>Add Application</h3>
            <form onSubmit={handleCreateApplication} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label className="section-label">Company</label>
                  <input required value={newApp.company} onChange={e => setNewApp({...newApp, company: e.target.value})} placeholder="Company Name" />
                </div>
                <div>
                  <label className="section-label">Title</label>
                  <input required value={newApp.title} onChange={e => setNewApp({...newApp, title: e.target.value})} placeholder="Job Title" />
                </div>
              </div>
              <div>
                <label className="section-label">Status</label>
                <select value={newApp.status} onChange={e => setNewApp({...newApp, status: e.target.value})}>
                  <option value="Wishlist">Wishlist</option>
                  <option value="Applied">Applied</option>
                  <option value="Interviewing">Interviewing</option>
                  <option value="Offer">Offer</option>
                  <option value="Rejected">Rejected</option>
                </select>
              </div>
              <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                <button type="button" className="btn-ghost" style={{ flex: 1 }} onClick={() => setShowAddModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary" style={{ flex: 2 }}>Track Application</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
