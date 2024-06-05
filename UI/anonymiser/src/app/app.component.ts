import { Component } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { NERService } from './ner.service';

export interface Highligtables {
  person: PersonMatch[];
  location: PersonMatch[];
  organisation: PersonMatch[];
  phone_numbers: string[];
  email_addresses: string[];
}

interface PersonMatch {
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
    person: [],
    location: [],
    organisation: [],
    phone_numbers: [],
    email_addresses: []
  };
  personalInfo: string[] = [];
  styledText: { text: string, type: string, isMatch: boolean, isSelected: boolean }[] = []
  persons: PersonMatch[] = [];
  selectedMatches: string[] = [];
  constructor(private NERservice: NERService) {}

  onFileSelected(event: any): void {
    this.fileToUpload = event.target.files[0];
  }

  togglePersonalInfo(word: string) {
    const index = this.personalInfo.indexOf(word);
    if(index > -1) {
      this.personalInfo.splice(index, 1);
    } else {
      this.personalInfo.push(word);
    }
  }

  onUpload(): void {
    if (this.userInput) {
      this.NERservice.getNamedEntities(this.userInput).subscribe(
        (response: Highligtables) => {
          this.wordsToHighlight  = response;
          this.styledText = this.getStyledText();
        },
        (error: HttpErrorResponse) => console.error('Upload error', error)
      );
    }
    if (this.fileToUpload && !this.userInput) {
      this.NERservice.getNamedEntitiesFile(this.fileToUpload).subscribe(
        (response: {highlightables: Highligtables, text: string}) => {
          this.userInput = response.text;
          this.wordsToHighlight = response.highlightables;
          this.styledText = this.getStyledText();
          console.log('Upload success', response)
        },
        (error: HttpErrorResponse) => console.error('Upload error', error)
      );
    }
  }

  getStyledText(): { text: string, type: string, isMatch: boolean, isSelected: boolean }[] {
    let cursor = 0;
    let result = [];

    // Combine all slots from persons, locations, and organisations and sort them by their starting positions
    const allSlots = [
        ...this.wordsToHighlight.person.reduce((acc: number[][], val) => acc.concat(val.slots), []),
        ...this.wordsToHighlight.location.reduce((acc: number[][], val) => acc.concat(val.slots), []),
        ...this.wordsToHighlight.organisation.reduce((acc: number[][], val) => acc.concat(val.slots), [])
    ].sort((a, b) => a[0] - b[0]);

    for (const slot of allSlots) {
        // Add non-matched text before the current slot
        if (cursor < slot[0]) {
            result.push({ text: this.userInput.substring(cursor, slot[0]), type: 'none', isMatch: false, isSelected: false });
        }
        // Extract the matched text and determine its type
        const matchedText = this.userInput.substring(slot[0], slot[1]);
        let type = 'none';
        if (this.wordsToHighlight.person.some(person => person.slots.some(s => s[0] === slot[0] && s[1] === slot[1]))) {
            type = 'person';
        } else if (this.wordsToHighlight.location.some(location => location.slots.some(s => s[0] === slot[0] && s[1] === slot[1]))) {
            type = 'location';
        } else if (this.wordsToHighlight.organisation.some(org => org.slots.some(s => s[0] === slot[0] && s[1] === slot[1]))) {
            type = 'organisation';
        }
        result.push({
            text: matchedText,
            type: type,
            isMatch: true,
            isSelected: this.selectedMatches.includes(matchedText)
        });
        cursor = slot[1]; // Move the cursor to the end of the current slot
    }

    // Add any remaining text after the last slot
    if (cursor < this.userInput.length) {
        result.push({ text: this.userInput.substring(cursor, this.userInput.length), type: 'none', isMatch: false, isSelected: false });
    }

    return result;
}

  getColor(part: { type: string, isSelected: boolean; isMatch: any; }): string {
    if (part.type === 'person') {
      return part.isSelected ? '#F0E8A2' : part.isMatch ? '#F4E771' : '#fff'
    }
    if (part.type === 'location') {
      return part.isSelected ? '#B6EEF5' : part.isMatch ? '#71E5F4' : '#fff'
    }
    if (part.type === "organisation") {
      return part.isSelected ? '#F9B1B1' : part.isMatch ? '#F47171' : '#fff'
    }
    return '#fff';
  }

  onMatchClick(match: string): void {
    if (this.selectedMatches.includes(match)) {
      this.selectedMatches = this.selectedMatches.filter(m => m !== match);
    } else {
      this.selectedMatches.push(match);
    }
  }
}
