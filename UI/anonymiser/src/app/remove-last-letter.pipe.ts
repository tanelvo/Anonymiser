// remove-last-letter.pipe.ts
import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'removeLastLetter'
})
export class RemoveLastLetterPipe implements PipeTransform {
  transform(value: string): string {
    if (!value) {
      return value;
    }
    return value.slice(0, -1); // Remove the last letter
  }
}
