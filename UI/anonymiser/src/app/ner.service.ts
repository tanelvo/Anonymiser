import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Highligtables } from './app.component';
import { HttpClient } from '@angular/common/http';

@Injectable({
  providedIn: 'root'
})
export class NERService {

  constructor(protected httpClient: HttpClient) { }

  getNamedEntities(text: string): Observable<Highligtables> {
    const body = {text};
    return this.httpClient.post<Highligtables>('https://invitations-extend-stops-manually.trycloudflare.com/text/', body);
  }

  getNamedEntitiesFile(file: File): Observable<Highligtables> {
    const formData: FormData = new FormData();
    formData.append('file', file, file.name);
    return this.httpClient.post<Highligtables>('https://invitations-extend-stops-manually.trycloudflare.com/file/', formData)
  }

  submitSelectedMatches(selectedMatches: any[], text: string, anonymize: string): Observable<any> {
    return this.httpClient.post<string>('https://invitations-extend-stops-manually.trycloudflare.com/anonymise/', { text: text, matches: selectedMatches, anonymize });
  }
}
