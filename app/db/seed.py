from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_session_factory
from app.models.document_type import DocumentType

SEED_DATA: list[dict] = [
    # ── Business Documents ────────────────────────────────────────────────────
    {
        "name": "Commercial Registration",
        "class_label": "commercial_registration",
        "subject_type": "business",
        "issuing_agency": "Ministry of Commerce",
        "description": (
            "Issued by the Ministry of Commerce. Contains a CR number, company legal name, "
            "business activity, registration and expiry dates. Also known as 'سجل تجاري'."
        ),
    },
    {
        "name": "Trade License",
        "class_label": "trade_license",
        "subject_type": "business",
        "issuing_agency": "Department of Economic Development (DED) / Municipality",
        "description": (
            "Issued by the DED or local municipality. Contains license number, licensed activities, "
            "trade name, owner name, issue and expiry dates. Also known as 'رخصة تجارية'."
        ),
    },
    {
        "name": "Establishment Card",
        "class_label": "establishment_card",
        "subject_type": "business",
        "issuing_agency": "Ministry of Human Resources and Emiratisation (MOHRE)",
        "description": (
            "Issued by MOHRE. Shows establishment number, company name, number of employees, "
            "and expiry date. Used for labour and work permit matters. Also known as 'بطاقة منشأة'."
        ),
    },
    {
        "name": "Article of Association",
        "class_label": "article_of_association",
        "subject_type": "business",
        "issuing_agency": "Ministry of Commerce / Notary Public",
        "description": (
            "Legal formation document listing shareholders, share capital, company objectives, "
            "and registered address. Usually notarized. Also known as 'عقد تأسيس'."
        ),
    },
    {
        "name": "Credit Bureau Report (Business)",
        "class_label": "credit_bureau_report_business",
        "subject_type": "business",
        "issuing_agency": "Al Etihad Credit Bureau (AECB) or equivalent",
        "description": (
            "Company credit report issued by AECB or similar body. Contains credit score, "
            "list of credit facilities, outstanding balances, and payment history."
        ),
    },
    {
        "name": "Tax Card",
        "class_label": "tax_card",
        "subject_type": "business",
        "issuing_agency": "Federal Tax Authority (FTA)",
        "description": (
            "Issued by the FTA showing the Tax Registration Number (TRN, 15 digits). "
            "Includes company name and effective VAT registration date."
        ),
    },
    {
        "name": "Payable Ageing Report",
        "class_label": "payable_ageing_report",
        "subject_type": "business",
        "issuing_agency": "Internal (company-generated)",
        "description": (
            "Shows outstanding amounts owed to vendors/suppliers, bucketed by time period "
            "(0-30, 31-60, 61-90, 90+ days). Usually exported from ERP/accounting software."
        ),
    },
    {
        "name": "Receivable Ageing Report",
        "class_label": "receivable_ageing_report",
        "subject_type": "business",
        "issuing_agency": "Internal (company-generated)",
        "description": (
            "Shows outstanding amounts owed by customers/debtors, bucketed by time period "
            "(0-30, 31-60, 61-90, 90+ days). Usually exported from ERP/accounting software."
        ),
    },
    {
        "name": "Bank Statement",
        "class_label": "bank_statement",
        "subject_type": "business",
        "issuing_agency": "Various banks",
        "description": (
            "Issued by a bank. Shows all account transactions for a period including IBAN, "
            "account holder name, opening/closing balance, and individual debit/credit entries. "
            "Format varies by bank."
        ),
    },
    {
        "name": "Audited Financial Report",
        "class_label": "audited_financial_report",
        "subject_type": "business",
        "issuing_agency": "Certified Public Accounting firms",
        "description": (
            "Prepared by a licensed external auditor. Contains auditor's opinion letter, "
            "balance sheet, income statement, cash flow statement, and notes to financial "
            "statements. Follows IFRS or local GAAP."
        ),
    },
    {
        "name": "Statement of Account",
        "class_label": "statement_of_account",
        "subject_type": "business",
        "issuing_agency": "Various suppliers / service providers",
        "description": (
            "Issued by a supplier or service provider. Summarises all transactions (invoices, "
            "payments, credits) showing opening balance, movement, and outstanding balance. "
            "Different from a bank statement — this is supplier-issued."
        ),
    },
    # ── Individual / Shareholder Documents ────────────────────────────────────
    {
        "name": "Passport",
        "class_label": "passport",
        "subject_type": "individual",
        "issuing_agency": "Government of issuing country",
        "description": (
            "International travel document issued by any country. All passports contain an MRZ "
            "(Machine Readable Zone) at the bottom with the holder's name, nationality, date of "
            "birth, and document number. Classifier trained on multi-country samples."
        ),
    },
    {
        "name": "QID (Qatar ID)",
        "class_label": "qid",
        "subject_type": "individual",
        "issuing_agency": "Ministry of Interior, Qatar",
        "description": (
            "Qatar National Identity Card issued by the Ministry of Interior. "
            "Fixed format with QID number, holder's name in Arabic and English, nationality, "
            "date of birth, and expiry date."
        ),
    },
    {
        "name": "National Address",
        "class_label": "national_address",
        "subject_type": "individual",
        "issuing_agency": "Government address authority",
        "description": (
            "Residential address certificate for a shareholder or individual, not a business address. "
            "Issued by the relevant government address authority."
        ),
    },
    {
        "name": "Credit Bureau Report (Individual)",
        "class_label": "credit_bureau_report_individual",
        "subject_type": "individual",
        "issuing_agency": "Al Etihad Credit Bureau (AECB) or equivalent",
        "description": (
            "Personal credit report for a shareholder or individual, issued by AECB or similar body. "
            "Contains personal credit score, credit facilities, and payment history. "
            "Distinct from the business credit bureau report."
        ),
    },
]


async def run_seed() -> None:
    factory = get_session_factory()
    async with factory() as session:
        async with session.begin():
            for data in SEED_DATA:
                existing = await session.execute(
                    select(DocumentType).where(DocumentType.class_label == data["class_label"])
                )
                if existing.scalar_one_or_none() is None:
                    session.add(DocumentType(**data))
