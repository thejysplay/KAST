# Mapper input limits

The mapper received the first **1,200 characters** of each message. Evidence beyond that limit may have
been omitted from the input used to produce the stored annotations.

The offline check flags **716 of 913** successful KAST runs containing a `messages[*].content` value longer than the limit.
It compares their stored `attempted` labels with the techniques already counted as `effect_observed`.
The count depends on which fields the parser reads. The effect of truncation on full-trace annotations has not been measured.
