import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Highligtables } from './app.component';
import { HttpClient } from '@angular/common/http';

export interface MorphologyToken {
  token: string;
  case: string;
  nominative: string;
  target_case_value: string;
}

export interface MorphologyResponse {
  text: string;
  target_case: string;
  combine_words: boolean;
  nominative_text: string;
  tokens: MorphologyToken[];
}

@Injectable({
  providedIn: 'root'
})
export class NERService {

  constructor(protected httpClient: HttpClient) { }

  BASE_URL = 'https://discrete-unlock-renaissance-forwarding.trycloudflare.com';

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

  getMorphology(text: string, targetCase: string, combineWords: boolean): Observable<MorphologyResponse> {
    return this.httpClient.post<MorphologyResponse>(this.BASE_URL + '/morphology/', {
      text,
      target_case: targetCase,
      combine_words: combineWords
    });
  }
}
