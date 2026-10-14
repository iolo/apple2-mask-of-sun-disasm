# apple2-mask-of-sun-korean

## GOAL

Korean translated version of the Apple II game "Mask of the Sun".

## INPUT

- Original disk images, materials and disassembled source code, assests and documents.
- Target machine: 48K Apple II(without 16K Language Card)

## OUTPUT

- Step1. Extract text to translate.
- Step2. Translate the extracted text into Korean.
- Step3. Request and confirm human review.
- Patch the original game with the translated Korean text.
- Target machine: 64K Apple II+(with 16K Language Card)

## Notes

- To simplify, no Korean Input Method.
- You might utilize 16K Language Card for Korean support.
- You might use [GamuriMono7 Font](https://github.com/quiple/galmuri/) which has 7x8 pixels glyph(8bytes per glyph) like general Apple II fonts. You can ignore readability(character-spacing, line-scacing) of the font.
- You might extract used glyphs(english and hangul syllables) from the translated text, and create a custom font to reduce size.
