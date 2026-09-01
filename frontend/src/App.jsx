import React, { useEffect, useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

function cleanText(value) {
  if (value === null || value === undefined) return "";

  return String(value)
    .replace(/â€”/g, "-")
    .replace(/â€“/g, "-")
    .replace(/â€™/g, "'")
    .replace(/â€œ/g, '"')
    .replace(/â€/g, '"')
    .replace(/â€¦/g, "...")
    .replace(/\uFFFD/g, "");
}

function formatCurrency(amount) {
  return `₹${Number(amount || 0).toLocaleString("en-IN")}`;
}

function statusClass(status) {
  switch (String(status || "").toLowerCase()) {
    case "recovered":
      return "status recovered";

    case "pending_approval":
      return "status pending";

    case "escalated":
      return "status escalated";

    case "rejected":
      return "status rejected";

    case "no_action":
      return "status neutral";

    default:
      return "status neutral";
  }
}

function statusLabel(status) {
  switch (String(status || "").toLowerCase()) {
    case "pending_approval":
      return "Pending Approval";

    case "recovered":
      return "Recovered";

    case "escalated":
      return "Escalated";

    case "rejected":
      return "Rejected";

    case "no_action":
      return "No Action";

    default:
      return status || "Unknown";
  }
}

function auditType(event) {
  const value = String(event || "").toLowerCase();

  if (
    value.includes("verified") ||
    value.includes("recovered") ||
    value.includes("executed")
  ) {
    return "audit-success";
  }

  if (value.includes("pending") || value.includes("approval")) {
    return "audit-pending";
  }

  if (
    value.includes("failed") ||
    value.includes("error") ||
    value.includes("rejected")
  ) {
    return "audit-failed";
  }

  if (value.includes("escalation")) {
    return "audit-escalation";
  }

  return "audit-neutral";
}

function auditIcon(event) {
  const value = String(event || "").toLowerCase();

  if (
    value.includes("verified") ||
    value.includes("recovered") ||
    value.includes("executed")
  ) {
    return "✓";
  }

  if (
    value.includes("failed") ||
    value.includes("error") ||
    value.includes("rejected")
  ) {
    return "✕";
  }

  if (value.includes("escalation")) {
    return "!";
  }

  if (value.includes("pending") || value.includes("approval")) {
    return "●";
  }

  return "•";
}

function App() {
  const [payments, setPayments] = useState([]);

  const [metrics, setMetrics] = useState({
    revenue_at_risk: 0,
    recovered_revenue: 0,
    recovery_rate: 0,
    pending_approvals: 0,
  });

  const [selectedPayment, setSelectedPayment] = useState(null);
  const [support, setSupport] = useState(null);
  const [audit, setAudit] = useState([]);

  const [loading, setLoading] = useState(true);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const [backendConnected, setBackendConnected] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  async function apiFetch(path, options = {}) {
    const response = await fetch(`${API}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });

    if (!response.ok) {
      let message = `HTTP ${response.status}`;

      try {
        const data = await response.json();

        if (data?.detail) {
          message += `: ${data.detail}`;
        }
      } catch {
        // Ignore invalid error JSON.
      }

      throw new Error(message);
    }

    return response.json();
  }

  async function loadDashboard() {
    setLoading(true);
    setErrorMessage("");

    try {
      const [paymentsData, metricsData] = await Promise.all([
        apiFetch("/payments"),
        apiFetch("/metrics"),
      ]);

      setPayments(paymentsData?.payments || []);

      setMetrics({
        revenue_at_risk: metricsData?.revenue_at_risk || 0,
        recovered_revenue: metricsData?.recovered_revenue || 0,
        recovery_rate: metricsData?.recovery_rate || 0,
        pending_approvals: metricsData?.pending_approvals || 0,
      });

      setBackendConnected(true);
    } catch (error) {
      console.error("Backend connection error:", error);

      setBackendConnected(false);

      setErrorMessage(
        `Unable to connect to RecoverAI backend at ${API}. ${error.message}`
      );
    } finally {
      setLoading(false);
    }
  }

  async function loadPaymentDetails(paymentId) {
    setReviewLoading(true);
    setErrorMessage("");

    try {
      const [supportData, auditData] = await Promise.all([
        apiFetch(`/support/${encodeURIComponent(paymentId)}`),
        apiFetch(`/audit/${encodeURIComponent(paymentId)}`),
      ]);

      setSupport(supportData);
      setAudit(auditData?.audit_log || []);
      setSelectedPayment(paymentId);
      setBackendConnected(true);
    } catch (error) {
      console.error("Review error:", error);

      setErrorMessage(
        `Unable to load payment ${paymentId}: ${error.message}`
      );
    } finally {
      setReviewLoading(false);
    }
  }

  async function refreshSelectedPayment(paymentId) {
    try {
      const [supportData, auditData] = await Promise.all([
        apiFetch(`/support/${encodeURIComponent(paymentId)}`),
        apiFetch(`/audit/${encodeURIComponent(paymentId)}`),
      ]);

      setSupport(supportData);
      setAudit(auditData?.audit_log || []);
      setSelectedPayment(paymentId);

      return true;
    } catch (error) {
      console.error("Refresh selected payment error:", error);

      setErrorMessage(
        `Unable to refresh ${paymentId}: ${error.message}`
      );

      return false;
    }
  }

  async function handleApprove() {
    if (!selectedPayment) return;

    setActionLoading(true);
    setErrorMessage("");

    try {
      await apiFetch(`/approve/${encodeURIComponent(selectedPayment)}`, {
        method: "POST",
      });

      await loadDashboard();
      await refreshSelectedPayment(selectedPayment);
    } catch (error) {
      console.error("Approve error:", error);

      setErrorMessage(`Approval failed: ${error.message}`);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleReject() {
    if (!selectedPayment) return;

    setActionLoading(true);
    setErrorMessage("");

    try {
      await apiFetch(`/reject/${encodeURIComponent(selectedPayment)}`, {
        method: "POST",
      });

      await loadDashboard();
      await refreshSelectedPayment(selectedPayment);
    } catch (error) {
      console.error("Reject error:", error);

      setErrorMessage(`Rejection failed: ${error.message}`);
    } finally {
      setActionLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  const analysis = support || {};

  const verification = analysis.verification || {};
  const checks = verification.checks || {};

  const policy = analysis.policy_decision || {};

  const escalations = Array.isArray(analysis.escalations)
    ? analysis.escalations
    : [];

  const reasons =
    analysis?.analysis?.reasons ||
    analysis?.reasons ||
    [];

  return (
    <div className="app">

      {/* SIDEBAR */}

      <aside className="sidebar">

        <div className="brand">

          <div className="brand-logo">
            R
          </div>

          <div>
            <div className="brand-name">
              RecoverAI
            </div>

            <div className="brand-subtitle">
              Revenue Recovery Agent
            </div>
          </div>

        </div>

        <nav className="navigation">

          <div className="nav-item active">
            <span>▦</span>
            Dashboard
          </div>

          <div className="nav-item">
            <span>⊙</span>
            Recovery
          </div>

          <div className="nav-item">
            <span>↗</span>
            Analytics
          </div>

          <div className="nav-item">
            <span>◷</span>
            History
          </div>

        </nav>

        <div className="agent-status">

          <div className="agent-dot"></div>

          <div>
            <strong>Agent Active</strong>
            <span>Monitoring payments</span>
          </div>

        </div>

      </aside>

      {/* MAIN */}

      <main className="main">

        <header className="page-header">

          <div>
            <h1>Revenue Recovery</h1>

            <p>
              Autonomous payment recovery intelligence
            </p>
          </div>

          <button
            className="refresh-button"
            onClick={loadDashboard}
            disabled={loading}
          >
            ↻ Refresh
          </button>

        </header>

        {/* CONNECTION */}

        {errorMessage && (
          <div className="connection-error">
            {errorMessage}
          </div>
        )}

        {!errorMessage && backendConnected && (
          <div className="connection-success">
            ✓ RecoverAI backend connected
          </div>
        )}

        {/* METRICS */}

        <section className="metrics-grid">

          <div className="metric-card">

            <div className="metric-top">
              <span>Revenue at Risk</span>

              <span className="metric-icon danger">
                ₹
              </span>
            </div>

            <strong>
              {formatCurrency(metrics.revenue_at_risk)}
            </strong>

            <small>
              Across failed payments
            </small>

          </div>

          <div className="metric-card">

            <div className="metric-top">
              <span>Recovered Revenue</span>

              <span className="metric-icon success">
                ✓
              </span>
            </div>

            <strong>
              {formatCurrency(metrics.recovered_revenue)}
            </strong>

            <small>
              Successfully recovered
            </small>

          </div>

          <div className="metric-card">

            <div className="metric-top">
              <span>Recovery Rate</span>

              <span className="metric-icon purple">
                %
              </span>
            </div>

            <strong>
              {Number(metrics.recovery_rate || 0).toFixed(1)}%
            </strong>

            <small>
              Current recovery performance
            </small>

          </div>

          <div className="metric-card">

            <div className="metric-top">
              <span>Pending Approvals</span>

              <span className="metric-icon warning">
                !
              </span>
            </div>

            <strong>
              {metrics.pending_approvals}
            </strong>

            <small>
              Require merchant review
            </small>

          </div>

        </section>

        {/* CONTENT */}

        <section className="content-grid">

          {/* PAYMENT TABLE */}

          <div className="panel payments-panel">

            <div className="panel-header">

              <div>
                <h2>Recovery Opportunities</h2>

                <p>
                  Payments identified as recoverable
                </p>
              </div>

              <span className="count-badge">
                {payments.length} payments
              </span>

            </div>

            <div className="table-wrapper">

              <table>

                <thead>

                  <tr>
                    <th>Payment</th>
                    <th>Amount</th>
                    <th>Failure</th>
                    <th>Probability</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>

                </thead>

                <tbody>

                  {payments.map((payment) => (

                    <tr
                      key={payment.payment_id}
                      className={
                        selectedPayment === payment.payment_id
                          ? "row-selected"
                          : ""
                      }
                    >

                      <td>

                        <div className="payment-id">
                          {payment.payment_id}
                        </div>

                        {payment.customer_id && (
                          <div className="customer-id">
                            {payment.customer_id}
                          </div>
                        )}

                      </td>

                      <td>
                        <strong>
                          {formatCurrency(payment.amount)}
                        </strong>
                      </td>

                      <td>
                        {cleanText(
                          payment.failure_reason || "-"
                        )}
                      </td>

                      <td>
                        <strong>
                          {Number(
                            payment.recovery_probability || 0
                          )}
                          %
                        </strong>
                      </td>

                      <td>

                        <span
                          className={statusClass(
                            payment.status
                          )}
                        >
                          {statusLabel(payment.status)}
                        </span>

                      </td>

                      <td>

                        <button
                          className="review-button"
                          onClick={() =>
                            loadPaymentDetails(
                              payment.payment_id
                            )
                          }
                          disabled={reviewLoading}
                        >
                          {reviewLoading &&
                          selectedPayment ===
                            payment.payment_id
                            ? "Loading..."
                            : "Review"}
                        </button>

                      </td>

                    </tr>

                  ))}

                  {!loading && payments.length === 0 && (

                    <tr>

                      <td
                        colSpan="6"
                        className="empty-state"
                      >
                        No payments found.
                      </td>

                    </tr>

                  )}

                </tbody>

              </table>

            </div>

          </div>

          {/* AI AGENT PANEL */}

          <div className="panel agent-panel">

            <div className="panel-header">

              <div>

                <h2>AI Recovery Agent</h2>

                <p>
                  Webhook → AI → Policy → Action →
                  Verification → Audit
                </p>

              </div>

              <span className="live-indicator">
                <span></span>
                LIVE
              </span>

            </div>

            {!support ? (

              <div className="agent-empty">

                <div className="agent-empty-icon">
                  ✦
                </div>

                <h3>
                  Select a payment
                </h3>

                <p>
                  Choose a recovery opportunity to see
                  the agent's full analysis, policy
                  decision, recovery action,
                  verification result, and audit trail.
                </p>

              </div>

            ) : (

              <div className="agent-content">

                {/* PAYMENT */}

                <div className="selected-payment">

                  <div>
                    <span>Analysis</span>

                    <strong>
                      {selectedPayment}
                    </strong>
                  </div>

                  <span
                    className={statusClass(
                      analysis.current_status
                    )}
                  >
                    {statusLabel(
                      analysis.current_status
                    )}
                  </span>

                </div>

                {/* RECOVERED AMOUNT */}

                {analysis.recovered_amount !== null &&
                  analysis.recovered_amount !== undefined && (

                    <div className="recovered-banner">

                      <span>
                        Recovered Amount
                      </span>

                      <strong>
                        {formatCurrency(
                          analysis.recovered_amount
                        )}
                      </strong>

                    </div>

                  )}

                {/* AI ANALYSIS */}

                <div className="agent-section">

                  <div className="section-title">
                    <span>01</span>
                    AI Analysis
                  </div>

                  <div className="analysis-grid">

                    <div className="analysis-item">

                      <label>
                        Recovery Score
                      </label>

                      <strong>
                        {analysis.recovery_score ??
                          analysis.recovery_probability ??
                          "-"}
                        {analysis.recovery_score !== null &&
                        analysis.recovery_score !== undefined
                          ? "%"
                          : ""}
                      </strong>

                    </div>

                    <div className="analysis-item">

                      <label>
                        Risk Level
                      </label>

                      <strong>
                        {cleanText(
                          analysis.risk_level || "-"
                        )}
                      </strong>

                    </div>

                    <div className="analysis-item">

                      <label>
                        Recommendation
                      </label>

                      <strong>
                        {cleanText(
                          analysis.recommendation || "-"
                        )}
                      </strong>

                    </div>

                    <div className="analysis-item">

                      <label>
                        AI Engine
                      </label>

                      <strong>
                        {cleanText(
                          analysis.ai_engine || "-"
                        )}
                      </strong>

                    </div>

                  </div>

                  {reasons.length > 0 && (

                    <div className="reasons">

                      <label>
                        Agent Reasoning
                      </label>

                      <ul>

                        {reasons.map(
                          (reason, index) => (

                            <li key={index}>
                              {cleanText(reason)}
                            </li>

                          )
                        )}

                      </ul>

                    </div>

                  )}

                </div>

                {/* POLICY */}

                <div className="agent-section">

                  <div className="section-title">
                    <span>02</span>
                    Policy Decision
                  </div>

                  <div className="policy-card">

                    <div>

                      <label>
                        Action
                      </label>

                      <strong>
                        {cleanText(
                          policy.action || "-"
                        )}
                      </strong>

                    </div>

                    <div>

                      <label>
                        Approval
                      </label>

                      <strong>
                        {policy.requires_merchant_approval
                          ? "Merchant Approval Required"
                          : "Automatic"}
                      </strong>

                    </div>

                    {policy.reason && (
                      <p>
                        {cleanText(policy.reason)}
                      </p>
                    )}

                  </div>

                </div>

                {/* RECOVERY */}

                <div className="agent-section">

                  <div className="section-title">
                    <span>03</span>
                    Recovery Action
                  </div>

                  <div className="recovery-card">

                    <label>
                      Action Taken
                    </label>

                    <strong>
                      {cleanText(
                        analysis.action_taken || "-"
                      )}
                    </strong>

                  </div>

                </div>

                {/* VERIFICATION */}

                <div className="agent-section">

                  <div className="section-title">
                    <span>04</span>
                    Verification
                  </div>

                  <div
                    className={
                      verification.verified
                        ? "verification-card verified"
                        : "verification-card failed"
                    }
                  >

                    <div className="verification-header">

                      <strong>
                        {verification.verified
                          ? "✓ Verified"
                          : "✕ Verification Failed"}
                      </strong>

                      <span>
                        {cleanText(
                          verification.message || ""
                        )}
                      </span>

                    </div>

                    <div className="checks-grid">

                      {[
                        [
                          "action_is_retry_payment",
                          "Action is retry payment",
                        ],
                        [
                          "amount_recorded",
                          "Amount recorded",
                        ],
                        [
                          "processor_confirmed",
                          "Processor confirmed",
                        ],
                        [
                          "amount_matches_expected",
                          "Amount matches expected",
                        ],
                      ].map(([key, label]) => (

                        <div
                          className={
                            checks[key]
                              ? "check pass"
                              : "check fail"
                          }
                          key={key}
                        >

                          <span>
                            {checks[key]
                              ? "✓"
                              : "✕"}
                          </span>

                          {label}

                        </div>

                      ))}

                    </div>

                  </div>

                </div>

                {/* ESCALATIONS */}

                {escalations.length > 0 && (

                  <div className="agent-section">

                    <div className="section-title">
                      <span>05</span>
                      Escalation
                    </div>

                    {escalations.map(
                      (escalation) => (

                        <div
                          className="escalation-card"
                          key={
                            escalation.escalation_id
                          }
                        >

                          <div className="escalation-header">

                            <strong>
                              {cleanText(
                                escalation.escalation_id
                              )}
                            </strong>

                            <span>
                              {cleanText(
                                escalation.severity
                              ).toUpperCase()}
                            </span>

                          </div>

                          <p>
                            <strong>
                              Reason:
                            </strong>{" "}
                            {cleanText(
                              escalation.reason
                            )}
                          </p>

                          <p>
                            <strong>
                              Status:
                            </strong>{" "}
                            {cleanText(
                              escalation.status
                            )}
                          </p>

                          <p>
                            <strong>
                              Recommended:
                            </strong>{" "}
                            {cleanText(
                              escalation.recommended_action
                            )}
                          </p>

                        </div>

                      )
                    )}

                  </div>

                )}

                {/* NEXT ACTION */}

                <div className="next-action">

                  <label>
                    Next Recommended Action
                  </label>

                  <strong>
                    {cleanText(
                      analysis.next_recommended_action ||
                        "-"
                    )}
                  </strong>

                </div>

                {/* APPROVAL BUTTONS */}

                {analysis.current_status ===
                "pending_approval" ? (

                  <div className="agent-actions">

                    <button
                      className="approve-button"
                      onClick={handleApprove}
                      disabled={actionLoading}
                    >
                      {actionLoading
                        ? "Processing..."
                        : "✓ Approve Recovery"}
                    </button>

                    <button
                      className="reject-button"
                      onClick={handleReject}
                      disabled={actionLoading}
                    >
                      {actionLoading
                        ? "Processing..."
                        : "✕ Reject"}
                    </button>

                  </div>

                ) : (

                  <div className="action-status-note">

                    No merchant action is available for
                    this payment because its current
                    status is{" "}

                    <strong>
                      {statusLabel(
                        analysis.current_status
                      )}
                    </strong>

                    .

                  </div>

                )}

                {/* AUDIT */}

                <div className="agent-section">

                  <div className="section-title">
                    <span>06</span>
                    Audit Trail
                  </div>

                  {audit.length === 0 ? (

                    <div className="audit-empty">
                      No audit events found.
                    </div>

                  ) : (

                    <div className="audit-timeline">

                      {audit.map(
                        (event, index) => {

                          const type =
                            auditType(event.event);

                          return (

                            <div
                              className={`audit-event ${type}`}
                              key={`${event.timestamp}-${index}`}
                            >

                              <div className="audit-marker">
                                {auditIcon(
                                  event.event
                                )}
                              </div>

                              <div className="audit-body">

                                <div className="audit-top">

                                  <strong>
                                    {cleanText(
                                      event.event
                                    )}
                                  </strong>

                                  <span>
                                    {new Date(
                                      event.timestamp
                                    ).toLocaleTimeString()}
                                  </span>

                                </div>

                                {event.details &&
                                  Object.keys(
                                    event.details
                                  ).length > 0 && (

                                    <pre>
                                      {JSON.stringify(
                                        event.details,
                                        null,
                                        2
                                      )}
                                    </pre>

                                  )}

                              </div>

                            </div>

                          );
                        }
                      )}

                    </div>

                  )}

                </div>

              </div>

            )}

          </div>

        </section>

        {/* HOW IT WORKS */}

        <section className="how-it-works">

          <div className="how-header">

            <h2>
              How RecoverAI Works
            </h2>

            <p>
              Autonomous revenue recovery pipeline
            </p>

          </div>

          <div className="pipeline">

            <div className="pipeline-step">

              <span>01</span>

              <strong>
                Detect
              </strong>

              <p>
                Identify failed payments and revenue
                at risk.
              </p>

            </div>

            <div className="pipeline-line"></div>

            <div className="pipeline-step">

              <span>02</span>

              <strong>
                Analyze
              </strong>

              <p>
                Determine root cause and recovery
                probability.
              </p>

            </div>

            <div className="pipeline-line"></div>

            <div className="pipeline-step">

              <span>03</span>

              <strong>
                Decide
              </strong>

              <p>
                Select the safest recovery intervention.
              </p>

            </div>

            <div className="pipeline-line"></div>

            <div className="pipeline-step">

              <span>04</span>

              <strong>
                Recover
              </strong>

              <p>
                Execute bounded recovery and measure
                results.
              </p>

            </div>

          </div>

        </section>

      </main>

    </div>
  );
}

export default App;