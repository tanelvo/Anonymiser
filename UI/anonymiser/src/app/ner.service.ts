import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Highligtables } from './app.component';
import { HttpClient } from '@angular/common/http';

export interface MorphologyToken {
  token: string;
  case: string;
  nominative: string;
}

export interface MorphologyResponse {
  text: string;
  nominative_text: string;
  tokens: MorphologyToken[];
}

@Injectable({
  providedIn: 'root'
})
export class NERService {

  constructor(protected httpClient: HttpClient) { }

  BASE_URL = 'https://invitations-extend-stops-manually.trycloudflare.com';

  getNamedEntities(text: string): Observable<Highligtables> {
    const body = {text};
    return this.httpClient.post<Highligtables>(this.BASE_URL + '/text/', body);
  }

  getNamedEntitiesFile(file: File): Observable<Highligtables> {
    const formData: FormData = new FormData();
    formData.append('file', file, file.name);
    return this.httpClient.post<Highligtables>(this.BASE_URL + '/file/', formData)
  }

  submitSelectedMatches(selectedMatches: any[], text: string, anonymize: string): Observable<any> {
    return this.httpClient.post<string>(this.BASE_URL + '/anonymise/', { text: text, matches: selectedMatches, anonymize });
  }

  getMorphology(text: string): Observable<MorphologyResponse> {
    return this.httpClient.post<MorphologyResponse>(this.BASE_URL + '/morphology/', { text });
  }
}
