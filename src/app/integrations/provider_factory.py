from app.core.config import settings
from app.core.exceptions import ProviderUnavailableError
from app.integrations.mock_category_provider import MockCategoryProvider
from app.integrations.mock_document_analysis_provider import MockDocumentAnalysisProvider
from app.integrations.openai_category_provider import OpenAICategoryProvider
from app.integrations.openai_document_analysis_provider import OpenAIDocumentAnalysisProvider


def build_document_analysis_provider():
    if settings.document_analysis_provider == "mock":
        return MockDocumentAnalysisProvider()
    if settings.document_analysis_provider == "openai":
        return OpenAIDocumentAnalysisProvider()
    raise ProviderUnavailableError(f"Unsupported analysis provider: {settings.document_analysis_provider}")


def build_category_provider():
    if settings.category_provider == "mock":
        return MockCategoryProvider()
    if settings.category_provider == "openai":
        return OpenAICategoryProvider()
    raise ProviderUnavailableError(f"Unsupported category provider: {settings.category_provider}")
