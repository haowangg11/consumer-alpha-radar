from router import ModelRouter


router = ModelRouter()


print(
    router.select_model(
        "financial_reasoning"
    )
)


print(
    router.select_model(
        "chinese_text"
    )
)