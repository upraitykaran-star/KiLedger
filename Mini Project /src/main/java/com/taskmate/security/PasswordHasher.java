package com.taskmate.security;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;
import java.security.*;
import java.util.*;
public final class PasswordHasher {
    private static final int ITERATIONS=210_000, KEY_BITS=256;
    private PasswordHasher() {}
    public static String hash(char[] password) {
        byte[] salt=new byte[16]; new SecureRandom().nextBytes(salt);
        byte[] derived=derive(password,salt,ITERATIONS,KEY_BITS);
        return "pbkdf2-sha256$"+ITERATIONS+"$"+Base64.getEncoder().encodeToString(salt)+"$"+Base64.getEncoder().encodeToString(derived);
    }
    public static boolean verify(char[] password,String encoded) {
        try { String[] p=encoded.split("\\$"); if(p.length!=4||!p[0].equals("pbkdf2-sha256")) return false; byte[] expected=Base64.getDecoder().decode(p[3]); return MessageDigest.isEqual(expected,derive(password,Base64.getDecoder().decode(p[2]),Integer.parseInt(p[1]),expected.length*8)); } catch(RuntimeException e){return false;}
    }
    private static byte[] derive(char[] password,byte[] salt,int iterations,int bits){ try { PBEKeySpec spec=new PBEKeySpec(password,salt,iterations,bits); try{return SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).getEncoded();} finally{spec.clearPassword();} } catch(GeneralSecurityException e){throw new IllegalStateException("PBKDF2 unavailable",e);} }
}
