from conversation_controller import ConversationManager

cm = ConversationManager()
print(f"\n✅ 11-STEP CONVERSATION FLOW:\n")
for i, step in enumerate(cm.flow, 1):
    print(f"Step {i}: {step['id']}")
    print(f"   Q: {step['q'][:70]}...")
    print(f"   Field: {step['field']}\n")
