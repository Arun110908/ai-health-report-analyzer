export default function AlertBanner({ report }) {
  return (
    <>
      {report.critical_alerts.length > 0 && (
        <div className="alert-banner">
          <div className="alert-head">
            <span className="status-dot off pulse" />
            <p className="alert-title">Critical findings</p>
          </div>
          <ul>
            {report.critical_alerts.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </div>
      )}
      {report.doctor_consultation_suggested && (
        <div className="doctor-note">
          <strong>Doctor consultation suggested. </strong>
          {report.doctor_consultation_reason}
        </div>
      )}
    </>
  );
}
