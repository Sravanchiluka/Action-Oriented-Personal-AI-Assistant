import React, { useEffect, useState } from "react";
import axios from "axios";

const API = "http://127.0.0.1:8000";

function ActivityTimeline() {
  const [activities, setActivities] = useState([]);

  useEffect(() => {
    axios
      .get(`${API}/activity`)
      .then((response) => setActivities(response.data.activities || []))
      .catch(() => setActivities([]));
  }, []);

  return (
    <div className="info-panel">
      <p className="eyebrow">Agent Trace</p>
      <h3>AI Activity Timeline</h3>
      {activities.length === 0 ? (
        <p className="empty-copy">No activity logged yet.</p>
      ) : (
        activities.map((activity, index) => (
          <div key={`${activity.timestamp}-${index}`} className="timeline-card">
            <div className="timeline-marker" />
            <div className="timeline-copy card">
              <strong>{activity.action}</strong>
              {activity.detail && <span>{activity.detail}</span>}
              {activity.timestamp && <small>{activity.timestamp}</small>}
            </div>
          </div>
        ))
      )}
    </div>
  );
}

export default ActivityTimeline;
