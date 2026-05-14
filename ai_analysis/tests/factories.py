import factory
from factory.django import DjangoModelFactory
from ai_analysis.models import AIAnalysis
from users.tests.factories import UserFactory
from diary.tests.factories import DiaryEntryFactory


class AIAnalysisFactory(DjangoModelFactory):
    class Meta:
        model = AIAnalysis

    user = factory.SubFactory(UserFactory)
    diary_entry = factory.SubFactory(
        DiaryEntryFactory,
        completed=True,
        user=factory.SelfAttribute('..user'),
    )
    prompt_sent = 'test prompt'
    raw_response = '{"mock": true}'
    summary = '這餐整體營養均衡。'
    suggestions = ['建議多補充蔬菜']
    exceeded_nutrients = ['鈉']
    lacking_nutrients = ['膳食纖維']
    nutrition_score = 75
    status = AIAnalysis.StatusChoices.COMPLETED
    ai_model_used = 'gemini:gemini-2.0-flash'
