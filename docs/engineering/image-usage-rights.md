# Image Usage Rights

**Last reviewed:** 2026-11-04
**Applies to:** SPEC-036 (practice candidate images), SPEC-043 (Pulse story
imagery), SPEC-045 (Learning Guide section images)

Fablit sources illustrative stock photography through one provider-neutral
`ImageSearchProvider` port (`fablit/application/image_search.py`) and one
concrete Pexafy adapter (`fablit/platform/pexafy_image_search.py`). Practice
authoring, Pulse story curation, and Learning Guides all reuse that boundary.

This note records the rights basis Fablit relies on, what it does **not**
guarantee, and the rule the Learning Guide publication gate enforces.

## 1. What Pexafy supplies

Pexafy is a semantic search engine over free-licence stock libraries, not an
image marketplace. Its [documentation](https://docs.pexafy.com/) says it
indexes nine sources: Unsplash, Pexels, Pixabay, Kaboompics, Burst, StockSnap,
Picjumbo, Skitterphoto, and NegativeSpace.

Each search result carries, among other fields:

- `source` — the source library (for example `Pexels` or `Pixabay`).
- `source_image_url` — the original photo page.
- `license_type` — the provider's machine-readable rights value (`free` or
  `cc0` in current responses; the API also exposes a licence facet).
- `photographer_full_name` / `photographer_username` / `photographer_url` —
  creator and creator page.
- `attribution.plain` — a ready-to-display credit line that also links to
  Pexafy's [licence summary](https://pexafy.com/legal/licenses/).
- CDN `image_url` and thumbnail URLs in several sizes.

## 2. What the guarantee is

Pexafy's [licence page](https://pexafy.com/legal/licenses/) states that all
sources in its index offer free licences allowing broad commercial use without
mandatory attribution. For the current sources, that includes:

- Use in websites, apps, editorial content, marketing, print, and products.
- Modification, cropping, and adaptation.
- Commercial use without payment or permission.
- Attribution optional (appreciated, but not a legal obligation).

The guarantee is **per photo and per source licence**, not a blanket grant from
Pexafy. Pexafy describes itself as a search engine, says each image is governed
by the licence of its source platform, and tells callers they are solely
responsible for verifying the licence before use — specifically by checking the
`license_type` field and reviewing the original source URL. Pexafy disclaims
liability for use that violates a source licence.

## 3. What it does not guarantee

Fablit must not read the provider relationship as broader than it is. The
sources do **not** guarantee:

- Indemnity or a legal warranty from Pexafy or the source library.
- Model or property releases. Identifiable people, private property,
  trademarks, and logos may still carry separate rights.
- That an image may be used as a trademark, logo, or brand identity. Pexels,
  for example, prohibits this explicitly.
- The right to sell unmodified copies, redistribute images as stock, or seed a
  competing image service.
- That source terms will never change. The source platform's current terms are
  authoritative.
- That a result without a `license_type` is usable. A missing value means the
  rights cannot be established from the provider response.

## 4. How Fablit uses the images

| Concern | Fablit behaviour |
| --- | --- |
| Display | A selected image may appear on a public learner page with its alt text and caption. |
| Attribution | Fablit shows the creator, source library, the provider's attribution line, and a link to the original source page, even though the current sources do not require attribution (SPEC-036 §10). |
| Modification | Fablit does not modify image bytes. The page scales the image responsively; no edited copy is stored. |
| Storage | Fablit persists metadata and provider URLs only — provider, asset id, source page, creator, attribution, licence, alt text, caption, query. No image bytes are downloaded or re-hosted. |
| Caching | Fablit keeps no server-side copy of the image. The browser or the provider's CDN may cache the image URL normally. |
| Hotlinking | Fablit renders the CDN URL returned by Pexafy directly and never proxies image bytes (SPEC-036 §10). |
| Illustrative labelling | Every guide figure is labelled “Illustrative stock image” so a generic photograph is not read as documentary evidence of a specific person, product, collection, or event (SPEC-045 §8.3). |
| Text-only fallback | A section remains fully usable without an image, including when rights cannot be established (SPEC-045 §8.3). |

The provider's terms, not the Fablit copy, remain authoritative. If a specific
image's durable display or rights cannot be established, the author should
choose another candidate or keep the section text-only.

## 5. Publication rule for Learning Guides

A guide image is publishable only when **all** of the following are present:

1. A provider-declared `license_type` on the selected image.
2. A source library and a safe absolute `http(s)` source page URL.
3. A creator or attribution credit.
4. Non-blank alt text.

`GuideImage.has_usage_rights` checks the licence, and
`GuideImage.has_provenance` requires both that and the source credit. The
publication gate names the offending asset and asks the author to remove it or
keep the section text-only.

The rule deliberately does **not** infer a licence from "Pexafy only indexes
free libraries". Pexafy's own guidance makes licence verification the caller's
responsibility, so a provider-level assumption would claim broader rights than
the provider actually grants. The authoring UI marks a candidate without a
licence as “Missing usage licence — cannot be published”, and the learner page
shows the licence that was retained with the image.
