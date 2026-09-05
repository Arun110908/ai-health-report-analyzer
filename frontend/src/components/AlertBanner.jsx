export default function AlertBanner({ report }) {
  return (
    <>
      {report.critical_alerts.length > 0 && (
        <div className="alert-banner">
          <p className="alert-title">Critical findings</p>
          <ul>
            {report.critical_alerts.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </div>
      )}
      {report.doctor_consultation_suggested && (
        <div className="doctor-note">
          <strong>Doctor consultation suggested.</strong>{" "}
          {report.doctor_consultation_reason}
        </div>
      )}
    </>
  );
}
