import { useEffect, useMemo, useState } from "react";

import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronRight,
  CircleDollarSign,
  Clock,
  CreditCard,
  Database,
  RefreshCw,
  ShieldCheck,
  XCircle,
} from "lucide-react";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import "./App.css";

// =========================================================
// BACKEND
// =========================================================

const API_BASE_URL = "http://127.0.0.1:8000";

// =========================================================
// DEMO DATA
// Used only when backend is unavailable
// =========================================================

const DEMO_PAYMENTS = [
  {
    payment_id: "pay_TWivUINC3yQh6J",
    amount: 200,
    currency: "INR",
    status: "failed",
    failure_reason: "payment_failed",
    retry_count: 0,

    razorpay_payment_id: "pay_TWivUINC3yQh6J",
    razorpay_method: "netbanking",

    metadata: {
      network: {
        bank: "BARB_R",
        wallet: null,
        vpa: null,
        acquirer_data: {
          bank_transaction_id: null,
        },
      },

      user: {
        international: false,
        contact: "+918586896584",
        email: "void@razorpay.com",
      },

      failure: {
        error_code: "BAD_REQUEST_ERROR",
        error_source: "bank",
        error_step: "payment_authorization",
        error_reason: "payment_failed",
        error_description:
          "Your payment didn't go through as it was declined by the bank.",
      },

      merchant_notes: {
        checkout_device: null,
        cart_session_duration_seconds: null,
        user_preferred_language: null,
      },

      raw_notes: {},
    },

    analysis: {
      recovery_score: 16,
      recovery_probability: 0.1627,
      risk_level: "HIGH",
      risk_tier: "HIGH",
      risk_label: "Low Recovery Potential",
      recommendation: "ESCALATE",

      root_cause:
        "The payment was declined by the issuing bank during payment authorization.",

      reasons: [
        "Payment has limited previous retry attempts.",
        "Razorpay error code: BAD_REQUEST_ERROR.",
        "Payment failure originated from BANK.",
        "Failure occurred during PAYMENT_AUTHORIZATION.",
        "Razorpay failure reason: PAYMENT_FAILED.",
        "Customer contact information is available for an approved recovery workflow.",
      ],

      ai_engine: "sklearn",
    },

    policy: {
      action: "DO_NOT_RETRY",
      requires_merchant_approval: false,
      probability: 0.1627,
      guardrail: "LOW_PROBABILITY",

      reason:
        "Recovery probability is below the safe intervention threshold.",

      max_attempts: 2,
    },
  },

  {
    payment_id: "pay_TX67XdhnQ0fEfb",
    amount: 20000,
    currency: "INR",
    status: "failed",
    failure_reason: "payment_failed",
    retry_count: 2,

    razorpay_payment_id: "pay_TX67XdhnQ0fEfb",
    razorpay_method: "netbanking",

    metadata: {
      network: {
        bank: "BARB_R",
        wallet: null,
        vpa: null,
        acquirer_data: {
          bank_transaction_id: null,
        },
      },

      user: {
        international: false,
        contact: "+918586896584",
        email: "void@razorpay.com",
      },

      failure: {
        error_code: "BAD_REQUEST_ERROR",
        error_source: "bank",
        error_step: "payment_authorization",
        error_reason: "payment_failed",
        error_description:
          "Your payment didn't go through as it was declined by the bank.",
      },

      merchant_notes: {
        checkout_device: null,
        cart_session_duration_seconds: null,
        user_preferred_language: null,
      },

      raw_notes: {
        source: "RecoverAI",
        type: "recovery",
        original_payment_id: "pay_TWivUINC3yQh6J",
        attempt: "1",
      },
    },

    analysis: {
      recovery_score: 16,
      recovery_probability: 0.1627,
      risk_level: "HIGH",
      risk_tier: "HIGH",
      risk_label: "Low Recovery Potential",
      recommendation: "ESCALATE",

      root_cause:
        "The payment was declined by the issuing bank during payment authorization.",

      reasons: [
        "Customer has more successful payments than failed payments.",
        "Customer has high lifetime value.",
        "Payment has already been retried 2 time(s).",
        "Razorpay error code: BAD_REQUEST_ERROR.",
        "Payment failure originated from BANK.",
        "Failure occurred during PAYMENT_AUTHORIZATION.",
        "Razorpay failure reason: PAYMENT_FAILED.",
        "Customer contact information is available for an approved recovery workflow.",
      ],

      ai_engine: "sklearn",
    },

    policy: {
      action: "DO_NOT_RETRY",
      requires_merchant_approval: false,
      probability: 0.1627,
      guardrail: "MAX_ATTEMPTS_REACHED",

      reason: "Recovery attempt limit reached.",

      max_attempts: 2,
    },
  },
];

// =========================================================
// HELPERS
// =========================================================

function formatCurrency(amount, currency = "INR") {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(Number(amount || 0));
}

function getPaymentId(payment) {
  return (
    payment?.payment_id ||
    payment?.razorpay_payment_id ||
    payment?.id ||
    "unknown"
  );
}

function getProbability(payment) {
  return Number(
    payment?.analysis?.recovery_probability ??
      payment?.policy?.probability ??
      0
  );
}

function getRisk(payment) {
  return (
    payment?.analysis?.risk_tier ||
    payment?.analysis?.risk_level ||
    "HIGH"
  ).toUpperCase();
}

function getAction(payment) {
  return (
    payment?.policy?.action ||
    payment?.action ||
    "DO_NOT_RETRY"
  );
}

function getBank(payment) {
  return (
    payment?.metadata?.network?.bank ||
    payment?.ml_features?.bank ||
    "UNKNOWN"
  );
}

function getErrorCode(payment) {
  return (
    payment?.metadata?.failure?.error_code ||
    payment?.ml_features?.error_code ||
    "UNKNOWN"
  );
}

function getErrorSource(payment) {
  return (
    payment?.metadata?.failure?.error_source ||
    payment?.ml_features?.error_source ||
    "UNKNOWN"
  );
}

function getErrorStep(payment) {
  return (
    payment?.metadata?.failure?.error_step ||
    payment?.ml_features?.error_step ||
    "UNKNOWN"
  );
}

function getErrorReason(payment) {
  return (
    payment?.metadata?.failure?.error_reason ||
    payment?.failure_reason ||
    "UNKNOWN"
  );
}

// =========================================================
// APP
// =========================================================

function App() {
  const [payments, setPayments] = useState([]);

  const [selectedPayment, setSelectedPayment] =
    useState(null);

  const [loading, setLoading] = useState(true);

  const [backendConnected, setBackendConnected] =
    useState(false);

  const [error, setError] = useState("");

  const [showMetadata, setShowMetadata] =
    useState(false);

  const [actionLoading, setActionLoading] =
    useState(false);

  const [actionMessage, setActionMessage] =
    useState("");

  // =======================================================
  // LOAD PAYMENTS
  // =======================================================

  useEffect(() => {
    loadPayments();
  }, []);

  async function loadPayments() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(
  `${API_BASE_URL}/dashboard/payments`
);

      if (!response.ok) {
        throw new Error(
          `Backend returned ${response.status}`
        );
      }

      const data = await response.json();

      let backendPayments = [];

      if (Array.isArray(data)) {
        backendPayments = data;
      } else if (Array.isArray(data.payments)) {
        backendPayments = data.payments;
      } else if (data.payments) {
        backendPayments = Object.values(
          data.payments
        );
      }

      if (backendPayments.length === 0) {
        throw new Error(
          "Backend returned no payments"
        );
      }

      setPayments(backendPayments);

      setSelectedPayment(
        backendPayments[0]
      );

      setBackendConnected(true);
    } catch (err) {
      console.warn(
        "Backend unavailable:",
        err
      );

      setPayments(DEMO_PAYMENTS);

      setSelectedPayment(
        DEMO_PAYMENTS[0]
      );

      setBackendConnected(false);

      setError(
        "Backend data unavailable. Showing local demo data."
      );
    } finally {
      setLoading(false);
    }
  }

  // =======================================================
  // SUMMARY
  // =======================================================

  const summary = useMemo(() => {
    let revenueAtRisk = 0;
    let recoverable = 0;
    let recovered = 0;
    let blocked = 0;

    payments.forEach((payment) => {
      const amount = Number(
        payment?.amount || 0
      );

      const action = getAction(payment);

      revenueAtRisk += amount;

      if (
        action === "AUTO_RETRY" ||
        action === "RETRY_WITH_APPROVAL"
      ) {
        recoverable += amount;
      }

      if (
        payment?.status === "recovered" ||
        payment?.processor_confirmed === true
      ) {
        recovered += amount;
      }

      if (
        action === "DO_NOT_RETRY" ||
        payment?.status === "blocked" ||
        payment?.status === "escalated"
      ) {
        blocked += amount;
      }
    });

    return {
      revenueAtRisk,
      recoverable,
      recovered,
      blocked,
    };
  }, [payments]);

  // =======================================================
  // GRAPH DATA
  // =======================================================

  const chartData = useMemo(() => {
    return payments.map((payment, index) => ({
      name:
        getPaymentId(payment) === "unknown"
          ? `Payment ${index + 1}`
          : getPaymentId(payment).slice(-8),

      amount: Number(
        payment?.amount || 0
      ),
    }));
  }, [payments]);

  // =======================================================
  // RECOVERY ACTION
  // =======================================================

  async function executeRecovery() {
    if (!selectedPayment) return;

    setActionLoading(true);
    setActionMessage("");

    try {
      const paymentId =
        getPaymentId(selectedPayment);

      const response = await fetch(
        `${API_BASE_URL}/recovery/order/${paymentId}`,
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data?.detail?.message ||
            data?.detail ||
            "Recovery action failed"
        );
      }

      setActionMessage(
        `Recovery order created: ${
          data.order_id || "success"
        }`
      );

      await loadPayments();
    } catch (err) {
      setActionMessage(
        err.message ||
          "Recovery action failed"
      );
    } finally {
      setActionLoading(false);
    }
  }

  // =======================================================
  // MERCHANT APPROVAL
  // =======================================================

  async function approveRecovery() {
    if (!selectedPayment) return;

    setActionLoading(true);
    setActionMessage("");

    try {
      const paymentId =
        getPaymentId(selectedPayment);

      const response = await fetch(
        `${API_BASE_URL}/recovery/approve/${paymentId}`,
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            "Approval failed"
        );
      }

      setActionMessage(
        data?.message ||
          `Recovery approval processed for ${paymentId}`
      );

      await loadPayments();
    } catch (err) {
      setActionMessage(
        err.message ||
          "Approval failed"
      );
    } finally {
      setActionLoading(false);
    }
  }

  // =======================================================
  // LOADING
  // =======================================================

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-content">
          <div className="loading-logo">
            RecoverAI
          </div>

          <div className="loading-text">
            Loading recovery intelligence...
          </div>
        </div>
      </div>
    );
  }

  // =======================================================
  // MAIN UI
  // =======================================================

  return (
    <div className="app">

      {/* =================================================
          HEADER
      ================================================= */}

      <header className="header">

        <div className="brand">

          <div className="brand-icon">
            <CircleDollarSign size={22} />
          </div>

          <div>
            <div className="brand-name">
              RecoverAI
            </div>

            <div className="brand-subtitle">
              AI Revenue Recovery
            </div>
          </div>

        </div>

        <div className="header-right">

          <button
            className="refresh-button"
            onClick={loadPayments}
            title="Refresh payments"
          >
            <RefreshCw size={16} />
            Refresh
          </button>

          <div className="connection-status">

            <span
              className={
                backendConnected
                  ? "status-dot online"
                  : "status-dot offline"
              }
            />

            {backendConnected
              ? "Backend Connected"
              : "Demo Mode"}

          </div>

        </div>

      </header>

      <main className="dashboard">

        {/* =================================================
            NOTICE
        ================================================= */}

        {error && (
          <div className="notice">
            <AlertTriangle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* =================================================
            SUMMARY
        ================================================= */}

        <section className="summary-grid">

          <SummaryCard
            icon={<CircleDollarSign />}
            label="Revenue at Risk"
            value={formatCurrency(
              summary.revenueAtRisk
            )}
          />

          <SummaryCard
            icon={<Clock />}
            label="Recoverable"
            value={formatCurrency(
              summary.recoverable
            )}
          />

          <SummaryCard
            icon={<CheckCircle2 />}
            label="Recovered"
            value={formatCurrency(
              summary.recovered
            )}
          />

          <SummaryCard
            icon={<ShieldCheck />}
            label="Blocked"
            value={formatCurrency(
              summary.blocked
            )}
          />

        </section>

        {/* =================================================
            MAIN CONTENT
        ================================================= */}

        <section className="content-grid">

          {/* =================================================
              LEFT
          ================================================= */}

          <div className="left-column">

            {/* =================================================
                PAYMENTS
            ================================================= */}

            <section className="panel">

              <div className="panel-header">

                <div>
                  <h2 className="panel-title">
                    Payment Recovery
                  </h2>

                  <p className="panel-subtitle">
                    Failed payments analyzed by RecoverAI
                  </p>
                </div>

                <div className="payment-count">
                  {payments.length} payments
                </div>

              </div>

              <div className="table-wrapper">

                <table className="payment-table">

                  <thead>
                    <tr>
                      <th>Payment ID</th>
                      <th>Amount</th>
                      <th>Risk</th>
                      <th>Probability</th>
                      <th>Policy</th>
                    </tr>
                  </thead>

                  <tbody>

                    {payments.map(
                      (payment, index) => {

                        const paymentId =
                          getPaymentId(payment);

                        const probability =
                          getProbability(payment);

                        const risk =
                          getRisk(payment);

                        const action =
                          getAction(payment);

                        const isSelected =
                          selectedPayment &&
                          getPaymentId(
                            selectedPayment
                          ) === paymentId;

                        return (
                          <tr
                            key={
                              paymentId !==
                              "unknown"
                                ? paymentId
                                : index
                            }
                            className={
                              isSelected
                                ? "payment-row selected"
                                : "payment-row"
                            }
                            onClick={() => {
                              setSelectedPayment(
                                payment
                              );

                              setShowMetadata(
                                false
                              );

                              setActionMessage(
                                ""
                              );
                            }}
                          >

                            <td>
                              <div className="payment-id">
                                {paymentId}
                              </div>
                            </td>

                            <td>
                              <strong>
                                {formatCurrency(
                                  payment.amount,
                                  payment.currency
                                )}
                              </strong>
                            </td>

                            <td>
                              <RiskBadge
                                risk={risk}
                              />
                            </td>

                            <td>
                              <span
                                className={
                                  probability >=
                                  0.75
                                    ? "probability probability-high"
                                    : probability >=
                                      0.45
                                    ? "probability probability-medium"
                                    : "probability probability-low"
                                }
                              >
                                {(
                                  probability * 100
                                ).toFixed(2)}
                                %
                              </span>
                            </td>

                            <td>
                              <span className="policy-mini">
                                {action}
                              </span>
                            </td>

                          </tr>
                        );
                      }
                    )}

                  </tbody>

                </table>

              </div>

            </section>

            {/* =================================================
                BAR GRAPH
            ================================================= */}

            <section className="panel chart-panel">

              <div className="panel-header">

                <div>
                  <h2 className="panel-title">
                    Revenue Exposure
                  </h2>

                  <p className="panel-subtitle">
                    Amount at risk per failed payment
                  </p>
                </div>

                <CircleDollarSign
                  size={20}
                  className="panel-icon"
                />

              </div>

              <div className="chart-container">

                {chartData.length > 0 ? (

                  <ResponsiveContainer
                    width="100%"
                    height={320}
                  >

                    <BarChart
                      data={chartData}
                      margin={{
                        top: 10,
                        right: 20,
                        left: 10,
                        bottom: 20,
                      }}
                    >

                      <CartesianGrid
                        strokeDasharray="3 3"
                        vertical={false}
                      />

                      <XAxis
                        dataKey="name"
                        tick={{
                          fontSize: 11,
                        }}
                      />

                      <YAxis
                        tick={{
                          fontSize: 11,
                        }}
                      />

                      <Tooltip
                        formatter={(value) =>
                          formatCurrency(
                            value
                          )
                        }
                      />

                      <Bar
                        dataKey="amount"
                        name="Amount at Risk"
                        radius={[
                          6,
                          6,
                          0,
                          0,
                        ]}
                      />

                    </BarChart>

                  </ResponsiveContainer>

                ) : (

                  <div className="empty-chart">
                    No payment data available.
                  </div>

                )}

              </div>

            </section>

          </div>

          {/* =================================================
              RIGHT
          ================================================= */}

          <div className="right-column">

            {selectedPayment && (

              <section className="panel selected-panel">

                <div className="panel-header">

                  <div>
                    <h2 className="panel-title">
                      Selected Payment
                    </h2>

                    <p className="panel-subtitle">
                      {getPaymentId(
                        selectedPayment
                      )}
                    </p>
                  </div>

                  <ChevronRight size={18} />

                </div>

                <div className="selected-payment">

                  {/* =================================================
                      PAYMENT DETAILS
                  ================================================= */}

                  <div className="detail-grid">

                    <Detail
                      label="Failure"
                      value={
                        selectedPayment.failure_reason ||
                        getErrorReason(
                          selectedPayment
                        )
                      }
                    />

                    <Detail
                      label="Bank"
                      value={getBank(
                        selectedPayment
                      )}
                    />

                    <Detail
                      label="Error"
                      value={getErrorCode(
                        selectedPayment
                      )}
                    />

                    <Detail
                      label="Source"
                      value={getErrorSource(
                        selectedPayment
                      )}
                    />

                    <Detail
                      label="Step"
                      value={getErrorStep(
                        selectedPayment
                      )}
                    />

                    <Detail
                      label="Attempts"
                      value={`${selectedPayment.retry_count || 0} / ${
                        selectedPayment
                          ?.policy
                          ?.max_attempts || 2
                      }`}
                    />

                    <Detail
                      label="Method"
                      value={
                        selectedPayment
                          ?.razorpay_method ||
                        "UNKNOWN"
                      }
                    />

                    <Detail
                      label="Probability"
                      value={`${(
                        getProbability(
                          selectedPayment
                        ) * 100
                      ).toFixed(2)}%`}
                    />

                  </div>

                  {/* =================================================
                      AI DIAGNOSIS
                  ================================================= */}

                  <div className="diagnosis-box">

                    <div className="section-heading">

                      <Bot size={17} />

                      <span>
                        AI Diagnosis
                      </span>

                    </div>

                    <p className="diagnosis-text">

                      {selectedPayment
                        ?.analysis
                        ?.root_cause ||
                        "No diagnosis available."}

                    </p>

                  </div>

                  {/* =================================================
                      AI REASONING
                  ================================================= */}

                  {selectedPayment
                    ?.analysis
                    ?.reasons
                    ?.length > 0 && (

                    <div className="reasons-box">

                      <div className="section-heading">

                        <Database size={16} />

                        <span>
                          AI Reasoning
                        </span>

                      </div>

                      <ul>

                        {selectedPayment.analysis.reasons
                          .slice(0, 8)
                          .map(
                            (
                              reason,
                              index
                            ) => (
                              <li key={index}>
                                {reason}
                              </li>
                            )
                          )}

                      </ul>

                    </div>

                  )}

                  {/* =================================================
                      POLICY
                  ================================================= */}

                  <div className="policy-box">

                    <div className="policy-header">

                      <div className="section-heading">

                        <ShieldCheck size={17} />

                        <span>
                          Recovery Policy
                        </span>

                      </div>

                      <PolicyBadge
                        action={getAction(
                          selectedPayment
                        )}
                      />

                    </div>

                    <p className="policy-reason">

                      {selectedPayment
                        ?.policy
                        ?.reason ||
                        "No policy reason available."}

                    </p>

                    <div className="guardrail">

                      <span>
                        Guardrail
                      </span>

                      <strong>
                        {selectedPayment
                          ?.policy
                          ?.guardrail ||
                          "UNKNOWN"}
                      </strong>

                    </div>

                  </div>

                  {/* =================================================
                      ACTION BUTTONS
                  ================================================= */}

                  <div className="action-buttons">

                    <button
                      className="btn"
                      onClick={() =>
                        setShowMetadata(
                          !showMetadata
                        )
                      }
                    >
                      <Database size={15} />

                      {showMetadata
                        ? "Hide Metadata"
                        : "View Metadata"}
                    </button>

                    {getAction(
                      selectedPayment
                    ) ===
                      "RETRY_WITH_APPROVAL" && (

                      <button
                        className="btn btn-primary"
                        onClick={
                          approveRecovery
                        }
                        disabled={
                          actionLoading
                        }
                      >

                        <CheckCircle2
                          size={15}
                        />

                        {actionLoading
                          ? "Processing..."
                          : "Approve Recovery"}

                      </button>
                    )}

                    {getAction(
                      selectedPayment
                    ) === "AUTO_RETRY" && (

                      <button
                        className="btn btn-primary"
                        onClick={
                          executeRecovery
                        }
                        disabled={
                          actionLoading
                        }
                      >

                        <CreditCard
                          size={15}
                        />

                        {actionLoading
                          ? "Creating..."
                          : "Recovery Action"}

                      </button>
                    )}

                  </div>

                  {/* =================================================
                      ACTION MESSAGE
                  ================================================= */}

                  {actionMessage && (

                    <div className="action-message">

                      {actionMessage}

                    </div>

                  )}

                  {/* =================================================
                      METADATA
                  ================================================= */}

                  {showMetadata && (

                    <div className="metadata-box">

                      <div className="metadata-header">
                        Razorpay Metadata
                      </div>

                      <pre>
                        {JSON.stringify(
                          selectedPayment
                            ?.metadata ||
                            {},
                          null,
                          2
                        )}
                      </pre>

                    </div>

                  )}

                </div>

              </section>

            )}

          </div>

        </section>

      </main>

    </div>
  );
}

// =========================================================
// SUMMARY CARD
// =========================================================

function SummaryCard({
  icon,
  label,
  value,
}) {
  return (
    <div className="summary-card">

      <div className="summary-top">

        <div className="summary-label">
          {label}
        </div>

        <div className="summary-icon">
          {icon}
        </div>

      </div>

      <div className="summary-value">
        {value}
      </div>

    </div>
  );
}

// =========================================================
// DETAIL
// =========================================================

function Detail({
  label,
  value,
}) {
  return (
    <div className="detail-item">

      <div className="detail-label">
        {label}
      </div>

      <div className="detail-value">
        {value}
      </div>

    </div>
  );
}

// =========================================================
// RISK BADGE
// =========================================================

function RiskBadge({ risk }) {
  const normalized =
    String(risk || "HIGH").toLowerCase();

  return (
    <span
      className={`badge badge-${normalized}`}
    >

      {normalized === "high" && (
        <XCircle size={12} />
      )}

      {normalized === "medium" && (
        <AlertTriangle size={12} />
      )}

      {normalized === "low" && (
        <CheckCircle2 size={12} />
      )}

      {String(risk).toUpperCase()}

    </span>
  );
}

// =========================================================
// POLICY BADGE
// =========================================================

function PolicyBadge({ action }) {
  let className = "policy-action";

  if (action === "AUTO_RETRY") {
    className += " policy-auto";
  }

  if (action === "RETRY_WITH_APPROVAL") {
    className += " policy-approval";
  }

  if (action === "DO_NOT_RETRY") {
    className += " policy-blocked";
  }

  return (
    <span className={className}>
      {action}
    </span>
  );
}

export default App;