import React, { useState, useEffect } from 'react';
import { 
    getIssueHistory, 
    getIssueComments, 
    addIssueComment,
    getStatuses,
    getPriorities,
    getSeverities,
    getCategories,
    getModules
} from '../../services/issueService';
import { getProjects } from '../../services/projectService';
import { getUsers } from '../../services/authService';
import { ActivitySentence } from '../../utils/activityHelper';

export default function IssueTimeline({ issueId, lookups: propLookups }) {
    const [events, setEvents] = useState([]);
    const [commentText, setCommentText] = useState('');
    const [loading, setLoading] = useState(true);
    const [internalLookups, setInternalLookups] = useState({});

    // Ensure lookups are available
    useEffect(() => {
        if (propLookups && Object.keys(propLookups).length > 0) {
            setInternalLookups(propLookups);
            return;
        }

        // Lazy load lookups if not passed as prop
        const fetchLookups = async () => {
            try {
                const [st, pr, sv, cat, mod, proj, usr] = await Promise.allSettled([
                    getStatuses(),
                    getPriorities(),
                    getSeverities(),
                    getCategories(),
                    getModules(),
                    getProjects(),
                    getUsers()
                ]);

                setInternalLookups({
                    statuses: st.status === 'fulfilled' ? st.value.data : [],
                    priorities: pr.status === 'fulfilled' ? pr.value.data : [],
                    severities: sv.status === 'fulfilled' ? sv.value.data : [],
                    categories: cat.status === 'fulfilled' ? cat.value.data : [],
                    modules: mod.status === 'fulfilled' ? mod.value.data : [],
                    allProjects: proj.status === 'fulfilled' ? proj.value.data : [],
                    allUsers: usr.status === 'fulfilled' ? (usr.value.data?.data || usr.value.data || []) : []
                });
            } catch (err) {
                console.error("Failed to load timeline lookups", err);
            }
        };

        fetchLookups();
    }, [propLookups]);

    const activeLookups = propLookups && Object.keys(propLookups).length > 0 ? propLookups : internalLookups;

    const loadTimeline = async () => {
        try {
            setLoading(true);
            const [historyRes, commentsRes] = await Promise.all([
                getIssueHistory(issueId),
                getIssueComments(issueId)
            ]);

            const combined = [
                ...(historyRes.data || []).map(h => ({ type: 'history', ...h })),
                ...(commentsRes.data || []).map(c => ({ type: 'comment', ...c }))
            ];

            // Sort newest first
            combined.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
            setEvents(combined);
        } catch (error) {
            console.error("Failed to load timeline", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (issueId) {
            loadTimeline();
        }
    }, [issueId]);

    const submitComment = async (e) => {
        e.preventDefault();
        if (!commentText.trim()) return;

        try {
            await addIssueComment(issueId, { content: commentText });
            setCommentText('');
            loadTimeline();
        } catch (error) {
            console.error("Failed to post comment", error);
        }
    };

    if (loading) {
        return (
            <div className="issue-timeline mt-4 text-center py-4 text-muted">
                <div className="spinner-border spinner-border-sm me-2" role="status"></div>
                Loading activity & comments…
            </div>
        );
    }

    return (
        <div className="issue-timeline mt-4">
            <h5 className="mb-3 d-flex align-items-center gap-2" style={{ fontWeight: 700, fontSize: '0.95rem', color: '#0f172a' }}>
                <span>💬</span> Activity & Comments
            </h5>
            
            <form onSubmit={submitComment} className="mb-4">
                <div className="form-group mb-2">
                    <textarea 
                        className="form-control" 
                        rows="3" 
                        placeholder="Add a comment to this issue..."
                        value={commentText}
                        onChange={(e) => setCommentText(e.target.value)}
                        style={{ fontSize: '0.9rem', borderRadius: '10px', borderColor: '#e2e8f0' }}
                    ></textarea>
                </div>
                <div className="d-flex justify-content-end">
                    <button 
                        type="submit" 
                        className="btn btn-primary btn-sm px-3" 
                        disabled={!commentText.trim()}
                        style={{ borderRadius: '8px', fontWeight: 600 }}
                    >
                        Post Comment
                    </button>
                </div>
            </form>

            <div className="timeline-events d-flex flex-column gap-2">
                {events.length === 0 ? (
                    <p className="text-muted text-center py-3" style={{ fontSize: '0.88rem' }}>No activity or comments recorded yet.</p>
                ) : (
                    events.map(event => (
                        <div 
                            key={`${event.type}-${event.id}`} 
                            className="timeline-event p-3 rounded"
                            style={{
                                background: event.type === 'comment' ? '#fff' : '#f8fafc',
                                border: '1px solid rgba(15,23,42,0.08)',
                                boxShadow: event.type === 'comment' ? '0 1px 4px rgba(15,23,42,0.04)' : 'none',
                                borderRadius: '10px'
                            }}
                        >
                            <div className="d-flex justify-content-between align-items-center text-muted small mb-1">
                                <span style={{ fontWeight: 600, color: event.type === 'comment' ? '#3b82f6' : '#475569', fontSize: '0.8rem' }}>
                                    {event.type === 'comment' ? '💬 Comment' : '📝 Activity'}
                                </span>
                                <span style={{ fontSize: '0.75rem' }}>{new Date(event.created_at).toLocaleString()}</span>
                            </div>
                            
                            {event.type === 'comment' ? (
                                <div>
                                    <div className="mb-1" style={{ fontSize: '0.85rem', fontWeight: 600, color: '#0f172a' }}>
                                        {event.user_name || 'User'}
                                    </div>
                                    <div style={{ whiteSpace: 'pre-wrap', fontSize: '0.9rem', color: '#334155', lineHeight: 1.5 }}>
                                        {event.content}
                                    </div>
                                </div>
                            ) : (
                                <div style={{ fontSize: '0.88rem', color: '#334155', lineHeight: 1.5 }}>
                                    <ActivitySentence event={event} lookups={activeLookups} />
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
