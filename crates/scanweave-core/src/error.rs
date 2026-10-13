//! Typed errors (SPEC §7). They carry page/span context but never default document text.

use thiserror::Error;

#[derive(Debug, Clone, PartialEq, Error)]
pub enum ScanWeaveError {
    #[error("InvalidInput: {context}")]
    InvalidInput { context: String },
    #[error("BindingMismatch: {context}")]
    BindingMismatch { context: String },
    #[error("MissingPhysicalGeometry: {context}")]
    MissingPhysicalGeometry { context: String },
    #[error("UnsupportedGeometry: {context}")]
    UnsupportedGeometry { context: String },
    #[error("UnsupportedDocumentFeature: {context}")]
    UnsupportedDocumentFeature { context: String },
    #[error("DependencyUnavailable: {context}")]
    DependencyUnavailable { context: String },
    #[error("ResourceLimit: limit={limit}: {context}")]
    ResourceLimit { limit: String, context: String },
    #[error("Cancelled")]
    Cancelled,
    #[error("ValidationFailed: {context}")]
    ValidationFailed { context: String },
    #[error("PolicyUnsatisfied: {context}")]
    PolicyUnsatisfied { context: String },
    #[error("IoFailure: {context}")]
    IoFailure { context: String },
    #[error("PublicationPartial: {context}")]
    PublicationPartial { context: String },
}
