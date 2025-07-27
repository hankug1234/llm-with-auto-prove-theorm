PROMPT = """

You previously attempted to reason about the following logical statement:

    {{ORIGINAL_STATEMENT}}

However, according to the tableau proof method, this argument is not fully valid. The following are the open branches from the attempted tableau proof—these represent possible models where the argument fails (i.e., no contradiction was found):

    {{OPEN_BRANCHES}}

These open branches indicate that your previous reasoning may have included a logical mistake, omission, or an invalid assumption.

Your tasks:

1. Analyze the open branches and identify any flaws or gaps in your previous reasoning.
2. Revise your original argument or conclusion if necessary.
3. Justify your revised answer with a clear logical explanation or example, ideally reflecting the structure of the open branches.

⚠️ Important: Do not simply repeat your original answer. You must acknowledge and respond to the implications of the open branches.

"""