# Automatic shelf suggestion

## Objective

BCD can automatically suggest a shelf when cataloguing a record. The
suggestion is a Top-1 autocomplete: it fills in the shelf field, which remains
manually editable at all times.

The feature is enabled by default. If no model is available, BCD keeps using
the existing static heuristic based on the media type.

## Data and storage

SQLite remains the catalogue source of truth and contains records, items,
and their shelves. Activation is not stored in SQLite: a valid trained JSON
artifact activates the feature. This makes the model artifact the single
source of truth for availability; the legacy `shelf_suggestion_enabled`
setting is ignored for activation.

The model is derived data and can be rebuilt. It is stored separately, like
cover images:

```text
data/
├── bcd.db
├── covers/
└── models/
    └── shelf_suggestion.json
```

The JSON file contains the classes, coefficients, vocabulary, version,
training date, and number of records used. It is written atomically: a
temporary file is replaced by the complete model. The `data/models/` directory
is ignored by Git.

If the model is deleted or missing after a restore, the application detects
that no valid JSON artifact exists, disables model suggestions, and falls back
to the heuristic. Training creates the artifact and activates the feature.

## Training

Training is **blocking and synchronous**. It is not started with
`BackgroundTasks`, and the interface does not poll: the request remains
pending until training and writing the file are complete.

Data is read from SQLite when the calculation starts. A record is retained
only when all its populated items share one non-empty shelf. A shelf must have
at least 10 records to be included.

The runtime engine and training are written in standard Python, without
scikit-learn, numpy, or scipy in the portable application. The model uses only:

- `title`;
- `subtitle`;
- `collection`;
- `authors`.

Feature extraction combines word and character n-grams with TF-IDF,
field-specific weights, and exact matches for collections and authors. The
final adjustment uses deterministic sparse multiclass SGD.

All available languages' stop-word lists are combined through
`stopwordsiso`, so the vocabulary is not limited to French catalogues.

The first calculation runs synchronously at startup if no model is present and
there is enough data. An administrator can also start a rebuild from the
catalogue settings.

## Data-science design

### Problem formulation

This is a supervised, multiclass classification problem. Each eligible
catalogue record is one observation, its shelf is the target label, and the
classifier must rank the configured shelves. The product deliberately exposes
only the highest-ranked class (Top-1), rather than pretending that the score is
an exact probability.

Shelf names are local, user-defined labels, so this is not a semantic ontology
or a recommendation against a universal classification scheme. The model
learns correlations in the school's own catalogue. Consequently, retraining is
appropriate after substantial cataloguing changes or after shelf organization
changes.

### Training population and label quality

The unit of learning is the bibliographic record, not an individual copy. A
record is included only when it has at least one populated item and all such
items have exactly one identical, non-empty shelf. This prevents contradictory
labels for the same title from teaching the model that one text belongs to
several classes. Records with multiple shelf locations are therefore treated as
ambiguous and excluded.

Classes with fewer than 10 records are excluded as well. This minimum support
is a pragmatic bias-variance trade-off: a class with one or two examples would
mostly memorize individual words and produce unstable coefficients. It also
makes the result visible and useful for the common shelves, while the existing
heuristic remains available for sparse catalogues.

### Text normalization and multilingual tokenization

Text is Unicode-normalized, accents are removed, and case is folded. Thus
`Éducation`, `education`, and `EDUCATION` share features. Fields that contain
author arrays or JSON-encoded arrays are converted into one searchable string.
Words are split on non-word characters, while character n-grams are generated
from the original normalized field with surrounding spaces.

The word vocabulary removes multilingual stop words using `stopwordsiso`.
This reduces function words that occur in many unrelated titles and avoids
assuming that every catalogue is French. Character features are retained even
when words are poorly tokenized, which helps with names, spelling variants,
accents, hyphenation, and multilingual text. Stop-word removal is applied only
to word n-grams, not character n-grams.

### Feature representation

For each of the four fields, the model creates:

- unigrams, bigrams, and trigrams of words;
- character n-grams of lengths 2 through 5;
- exact-match features for `collection` and `authors`.

Word n-grams capture interpretable phrases such as a subject or series name;
character n-grams provide robustness for partial words and metadata variation.
Collection and author exact matches receive separate features because these
fields are often strong catalogue-specific signals, and an exact match should
not be diluted by the general text vocabulary.

Each word/character block is L2-normalized independently. Field weights then
encode a conservative prior: collection (2.8) and authors (2.2) are generally
more discriminative than title (1.1), while subtitle (0.6) is supporting
evidence. Character blocks receive 80% of their field's word-block weight.
The resulting complete vector is normalized again so long records do not win
simply because they contain more terms.

### TF-IDF and vocabulary control

For a term appearing in `df` of `N` training records, the inverse document
frequency is:

```text
idf(term) = log((1 + N) / (1 + df(term))) + 1
```

Term frequency uses `1 + log(count)`, preventing repeated words from growing
linearly. Terms occurring in fewer than three records are removed to limit
memorization and artefact size. General terms occurring in more than 95% of
records are also removed because they cannot distinguish shelves. Exact
collection and author features are exempt from the upper-frequency rule and
are kept when observed at least twice.

### Classifier and inference

The final model is a sparse linear multiclass classifier trained with a
one-versus-the-strongest-competitor hinge-loss update. For each training row,
the true class is promoted and the highest-scoring incorrect class is
penalized whenever its margin is less than 1. This is a compact margin-based
alternative to a full probabilistic model and works well with sparse text
vectors.

Training uses three epochs, a learning rate of 0.05 with decay 0.0002, and a
fixed random seed (`42`) for shuffling. These deliberately modest settings
keep synchronous training fast on old school computers and make the same input
produce the same JSON model. At inference, class scores are the intercept plus
the dot product of the sparse vector and the stored coefficients; classes are
sorted by descending score, with shelf name as a deterministic tie-breaker.

The implementation stores only non-zero coefficients and vocabulary metadata.
It therefore needs no matrix package at runtime and can load the JSON model
without re-running training.

### Why this model rather than a larger one?

A neural language model would require substantially more memory, introduce
platform-specific native dependencies, and learn poorly from the small,
school-specific datasets available here. A linear sparse model is transparent,
fast, deterministic, portable, and easy to rebuild when labels change. It also
makes feature contributions inspectable during maintenance. The trade-off is
that it does not understand meaning or synonyms beyond the observed word and
character patterns; the static media-type heuristic and manual editing remain
intentional safety nets.

### Evaluation and limitations

The reported benchmark metrics compare Top-1 and Top-3 ranking quality,
balanced accuracy (to avoid large shelves dominating the result), and macro F1
(to measure performance across shelves). They are useful diagnostics, not a
guarantee for another school's catalogue. The current product uses Top-1 only.
A future evaluation should use a held-out, time-based split so records from the
same series or import batch do not leak between training and validation, and
should report per-shelf support and a confusion matrix. No confidence threshold
is currently applied: a suggestion is advisory, never an automatic overwrite.

## API

```text
GET  /api/v1/admin/shelf-suggestion/status
POST /api/v1/admin/shelf-suggestion/train
POST /api/v1/catalog/shelf-suggestion
```

The suggestion response always has this form:

```json
{"suggested_shelf": "Fiction"}
```

or `null` if no valid model JSON artifact is present.

## Interface

In the catalogue settings, an administrator can:

- enable or disable automatic suggestions;
- see whether the model is ready and how many records were used for training;
- click “Train now”.

When cataloguing, the model suggestion can replace the static heuristic only
when the shelf field is still empty or still contains a value generated
automatically. Manual input is never overwritten.

## Validation

The benchmark protocol covers 2,770 records, including 2,541 evaluable records
and 22 shelves. The reference models available in the preparatory work achieved:

| Model | Top-1 | Top-3 | Balanced accuracy | Macro F1 |
|---|---:|---:|---:|---:|
| GO 4 fields | 69.15% | 85.12% | 49.51% | 36.53% |
| CL 4 fields | 69.58% | 85.56% | 49.51% | 41.37% |
| ZE pure Python | 67.41% | 82.37% | 49.71% | 40.44% |
| BCD pure-Python engine | 65.84% | 81.86% | 43.29% | 43.74% |

Integration tests cover the minimum threshold, exclusion of ambiguous
records, model persistence, and Top-1 prediction.
