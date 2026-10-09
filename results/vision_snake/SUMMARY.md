# Vision Snake, clef-flash

## Single moves

| Request | Good pick, all / hard | Straight on hard | Fatal pick, all / hard | Per move |
|---|--:|--:|--:|--:|
| see-4-blocks | 0.83 / 0.74 | 0.26 | 0.06 / 0.00 | 1137 ms |
| see-legal-blocks | 0.98 / 0.98 | 0.02 | 0.00 / 0.00 | 1112 ms |
| see-ask-blocks | 0.82 / 0.73 | 0.23 | 0.02 / 0.00 | 2564 ms |
| see-4-blocks-2f | 0.83 / 0.66 | 0.34 | 0.07 / 0.00 | 1788 ms |
| see-legal-blocks-2f | 0.92 / 0.78 | 0.21 | 0.00 / 0.00 | 1817 ms |
| see-ask-blocks-2f | 0.81 / 0.59 | 0.39 | 0.01 / 0.00 | 3170 ms |

## Games

| Request | Food mean / best | Steps, median | Died | Starved | Per model call |
|---|--:|--:|--:|--:|--:|
| clef-flash-see-4-blocks | 1.1 / 5 | 8 | 10 of 10 | 0 | 1129 ms |
| clef-flash-see-ask-blocks | 1.2 / 2 | 44 | 6 of 10 | 4 | 2604 ms |
| clef-flash-see-legal-blocks | 25.2 / 39 | 260 | 9 of 10 | 0 | 1124 ms |
