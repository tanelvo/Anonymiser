import { Component } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { NERService } from './ner.service';

export interface Highligtables {
  text: string;
  person: Match[];
  location: Match[];
  organisation: Match[];
  phone_numbers: Match[];
  email_addresses: Match[];
  id_numbers: Match[];
  count: number;
}

interface Match {
  match: string;
  slots: number[][];
}

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  fileToUpload: File | null = null;
  userInput: string = '';
  wordsToHighlight: Highligtables = {
    text: "",
    person: [],
    location: [],
    organisation: [],
    phone_numbers: [],
    email_addresses: [],
    id_numbers: [],
    count: 0
  };
  personalInfo: string[] = [];
  styledText: { text: string, type: string, isMatch: boolean, isSelected: boolean }[] = []
  persons: Match[] = [];
  isCustomizable: boolean = false;
  constructor(private NERservice: NERService) {}

  processedText: any[] = [];
  selectedMatches: { match: string; custom?: string }[] = [];
  anomyizedText: string = '';
  anonymizeOption: string = "words";

  onFileSelected(event: any): void {
    this.fileToUpload = event.target.files[0];
  }

  onUpload(): void {
    this.processedText = [];
    this.selectedMatches = [];
    if (this.userInput) {
      this.NERservice.getNamedEntities(this.userInput).subscribe(
        (response: Highligtables) => {
          this.wordsToHighlight = response;
          this.processText(response);
          console.log('Upload success', response);
        },
        (error: HttpErrorResponse) => console.error('Upload error', error)
      );
    }
    if (this.fileToUpload && !this.userInput) {
      this.NERservice.getNamedEntitiesFile(this.fileToUpload).subscribe(
        (response: Highligtables) => {
          this.wordsToHighlight = response;
          this.processText(response);
          console.log('Upload success', response);
        },
        (error: HttpErrorResponse) => console.error('Upload error', error)
      );
    }
  }

  processText(data: Highligtables): void {
    let text = data.text;
    const entities = [
      { type: 'person', color: '#F4E771', selected: '#F0E8A2' },
      { type: 'organisation', color: '#F47171', selected: '#F9B1B1' },
      { type: 'location', color: '#71E5F4', selected: '#B6EEF5' },
      { type: 'phone_numbers', color: '#FFB347', selected: '#FFD580' },
      { type: 'email_addresses', color: '#D885F7', selected: '#E4A9F9' },
      { type: 'id_numbers', color: '#6ec27f', selected: '#92d19f' },
    ];
  
    // Adjusted positions due to the added <br> tags
    const newlineIndices: number[] = [];
    for (let i = 0; i < text.length; i++) {
      if (text[i] === '\n') {
        newlineIndices.push(i);
      }
    }
  
    // Replace \n with <br> in the text
    text = text.replace(/\n/g, '<br>');
  
    let slots: any[] = [];
    entities.forEach(entity => {
      const entityType = entity.type as keyof Highligtables;
      const entityData = data[entityType];
      if (Array.isArray(entityData)) {
        entityData.forEach((matchObj: any) => {
          matchObj.slots.forEach((slot: any) => {
            // Adjust slot positions based on the additional <br> lengths
            const adjustedSlot = this.adjustSlotForNewlines(slot, newlineIndices);
            slots.push({ ...adjustedSlot, match: matchObj.match, type: entity.type, color: entity.color, selected: entity.selected });
          });
        });
      }
    });
    slots.sort((a: any, b: any) => a[0] - b[0]);
  
    let lastIndex = 0;
    slots.forEach(slot => {
      if (lastIndex < slot[0]) {
        this.processedText.push({ text: text.substring(lastIndex, slot[0]), normal: true });
      }
      this.processedText.push({
        text: text.substring(slot[0], slot[1]),
        normal: false,
        match: slot.match,
        type: slot.type,
        color: slot.color,
        selected: slot.selected
      });
      lastIndex = slot[1];
    });
    if (lastIndex < text.length) {
      this.processedText.push({ text: text.substring(lastIndex), normal: true });
    }
  }
  
  // Function to adjust slot positions for the added <br> elements
  adjustSlotForNewlines(slot: number[], newlineIndices: number[]): number[] {
    const [start, end] = slot;
    let shiftStart = 0;
    let shiftEnd = 0;
  
    // For each newline, adjust start and end positions based on where the newline is
    newlineIndices.forEach(index => {
      if (index < start) {
        shiftStart += 3; // Each \n is replaced by <br>, which adds 3 characters
      }
      if (index < end) {
        shiftEnd += 3;
      }
    });
  
    return [start + shiftStart, end + shiftEnd];
  }

  submitSelections(): void {
    const selectedMatchesData = this.selectedMatches.map(match => {
      // Find the corresponding Match object from wordsToHighlight to get the slots
      const entityTypeKeys = Object.keys(this.wordsToHighlight).filter(
        key => Array.isArray(this.wordsToHighlight[key as keyof Highligtables])
      ) as (keyof Highligtables)[];
  
      let slots: number[][] = [];
      let matchType: string | undefined;
  
      entityTypeKeys.forEach(entityType => {
        const entityMatches = this.wordsToHighlight[entityType] as Match[];
        const matchedEntity = entityMatches.find((m: Match) => m.match === match.match);
        if (matchedEntity) {
          slots = matchedEntity.slots;
          matchType = entityType;
        }
      });
  
      return {
        match: match.match,
        slots: slots,
        custom: match.custom || null,
        type: matchType
      };
    });
  
    // Send the request with selected matches
    this.NERservice.submitSelectedMatches(selectedMatchesData, this.wordsToHighlight.text, this.anonymizeOption).subscribe(
      response => {
        this.anomyizedText = response;
        console.log(this.anomyizedText);
      },
      (error: HttpErrorResponse) => {
        console.error('Error submitting selections', error);
      }
    );
  }
  

  selectMatch(match: string): void {
    const existingMatch = this.selectedMatches.find(m => m.match === match);
    if (!existingMatch) {
      this.selectedMatches.push({ match });
    } else {
      this.selectedMatches = this.selectedMatches.filter(m => m.match !== match);
    }
  }

  get formattedVariable(): string {
    return this.anomyizedText.replace(/\n/g, '<br>');
  }

  toggleAllSelections(): void {
    if (this.selectedMatches.length === this.wordsToHighlight.count) {
      this.selectedMatches = [];
    } else {
      this.selectedMatches = this.processedText
        .filter(part => !part.normal)
        .map(part => ({ match: part.match }))
        .filter((value, index, self) => self.findIndex(v => v.match === value.match) === index);
    }
  }

  getHighlightColor(match: string): string {
    const matchedEntity = this.processedText.find(part => part.match === match);
    return matchedEntity ? (this.isSelected(match) ? matchedEntity.selected : matchedEntity.color) : 'transparent';
  }

  removeMatch(match: string): void {
    this.selectedMatches = this.selectedMatches.filter(m => m.match !== match);
  }

  isSelected(match: string): boolean {
    return this.selectedMatches.some(m => m.match === match);
  }
}
