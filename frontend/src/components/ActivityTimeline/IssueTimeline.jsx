import React, { useState, useEffect } from 'react';
import { getIssueHistory, getIssueComments, addIssueComment } from '../../services/issueService';

export default function IssueTimeline({ issueId }) {
    const [events, setEvents] = useState([]);
    const [commentText, setCommentText] = useState('');
    const [loading, setLoading] = useState(true);

    const loadTimeline = async () => {
        try {
            setLoading(true);
            const [historyRes, commentsRes] = await Promise.all([
                getIssueHistory(issueId),
                getIssueComments(issueId)
            ]);

            const combined = [
                ...historyRes.data.map(h => ({ type: 'history', ...h })),
                ...commentsRes.data.map(c => ({ type: 'comment', ...c }))
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

    if (loading) return <div>Loading timeline...</div>;

    return (
        <div className="issue-timeline mt-4">
            <h5 className="mb-3">Activity & Comments</h5>
            
            <form onSubmit={submitComment} className="mb-4">
                <div className="form-group mb-2">
                    <textarea 
                        className="form-control" 
                        rows="3" 
                        placeholder="Add a comment..."
                        value={commentText}
                        onChange={(e) => setCommentText(e.target.value)}
                    ></textarea>
                </div>
                <button type="submit" className="btn btn-primary btn-sm" disabled={!commentText.trim()}>
                    Post Comment
                </button>
            </form>

            <div className="timeline-events">
                {events.length === 0 ? (
                    <p className="text-muted">No activity yet.</p>
                ) : (
                    events.map(event => (
                        <div key={`${event.type}-${event.id}`} className={`timeline-event mb-3 p-3 border rounded ${event.type === 'comment' ? 'bg-light' : ''}`}>
                            <div className="d-flex justify-content-between text-muted small mb-1">
                                <strong>{event.user_name}</strong>
                                <span>{new Date(event.created_at).toLocaleString()}</span>
                            </div>
                            
                            {event.type === 'comment' ? (
                                <div className="mt-2" style={{ whiteSpace: 'pre-wrap' }}>
                                    {event.content}
                                </div>
                            ) : (
                                <div className="mt-1">
                                    Changed <strong>{event.field_name}</strong> from 
                                    <span className="badge bg-secondary mx-1">{event.old_value && event.old_value !== 'None' ? event.old_value : '-'}</span> 
                                    to 
                                    <span className="badge bg-primary mx-1">{event.new_value && event.new_value !== 'None' ? event.new_value : '-'}</span>
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
