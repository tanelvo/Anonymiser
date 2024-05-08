import { Component } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { NERService } from './ner.service';

export interface Highligtables {
  person: string[];
  location: string[];
  organisation: string[];
  phone_numbers: string[];
  email_addresses: string[];
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
          console.log('Upload success', response)
        },
        (error: HttpErrorResponse) => console.error('Upload error', error)
      );
    }
    if (this.fileToUpload && !this.userInput) {
      this.NERservice.getNamedEntitiesFile(this.fileToUpload).subscribe(
        (response: {highlightables: Highligtables, text: string}) => {
          this.userInput = response.text;
          this.wordsToHighlight = response.highlightables;
          console.log('Upload success', response)
        },
        (error: HttpErrorResponse) => console.error('Upload error', error)
      );
    }

  }
}
