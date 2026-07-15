from router import ModelRouter


router = ModelRouter()


print(
    router.select_model(
        "financial_analysis"
    )
)


print(
    router.select_model(
        "trend_discovery"
    )
)